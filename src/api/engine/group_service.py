"""Group / network risk — an economic group is the connected component of
customers linked through shared parties (a common UBO, a shared director, a
parent sitting above several structures, one actor across many entities).

AML risk is contagious across a group: a file is only as clean as its dirtiest
relative, and a shared PEP or a high-risk sister company should colour the
review of every entity it touches. This module derives the group LIVE from the
ownership graph — nothing is persisted, so it always reflects the current
structure — and aggregates the members' already-versioned, explainable risk
into a group view.

It never silently rewrites a member's own score; it surfaces the *inherited*
signal and lets the officer act, in keeping with the platform's
suggest-and-confirm stance (the same choice made for identity resolution).
"""
from api.models import Customer, Party
from api.engine import ownership
from api.engine.party_service import party_links

_LEVEL_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_HIGH = _LEVEL_ORDER["HIGH"]


def _rank(level):
    return _LEVEL_ORDER.get(level, 0)


def _peak(levels):
    best = "LOW"
    for lv in levels:
        if _rank(lv) > _rank(best):
            best = lv
    return best


def _customer_party_ids(customer):
    """Every party in the customer's ownership graph (root + all owners,
    directors and controllers reachable from it)."""
    return {n["id"] for n in ownership.build_graph(customer)["nodes"]}


def _latest_assessment(customer):
    best = None
    for a in customer.assessments:
        if best is None or (a.id or 0) > (best.id or 0):
            best = a
    return best


def build_group(customer):
    """The connected component of customers reachable from `customer` through
    shared parties. Bipartite breadth-first walk over customers <-> parties: a
    customer touches the parties of its ownership graph; a party touches every
    customer it is the subject of or an owner in. Returns the member customer
    ids and the bridge parties (each shared by >= 2 members)."""
    members = {customer.id}
    seen_parties = set()
    queue = [customer]
    bridges = {}          # party_id -> {"party": Party, "customers": set(cid)}
    while queue:
        c = queue.pop()
        for pid in _customer_party_ids(c):
            if pid in seen_parties:
                continue
            seen_parties.add(pid)
            p = Party.query.get(pid)
            if p is None:
                continue
            touched = {l["customer_id"] for l in party_links(p)
                       if l.get("customer_id")}
            for cid in touched:
                if cid not in members:
                    members.add(cid)
                    nc = Customer.query.get(cid)
                    if nc is not None:
                        queue.append(nc)
            if len(touched) >= 2:      # links two+ of our files => a real bridge
                bridges[pid] = {"party": p, "customers": touched}
    return {"member_ids": members, "bridges": bridges}


def group_risk(customer):
    """Aggregate the group's risk: peak level (a group is as risky as its worst
    member), the level distribution, every member with its own score, the bridge
    actors that hold the group together (a shared PEP is a red flag in itself),
    and the drivers behind the elevated members. `inherited` is the key signal —
    True when the group peaks higher than this file scores on its own, i.e. the
    network warrants an enhanced review even though the entity looks clean."""
    group = build_group(customer)
    members = [c for c in (Customer.query.get(cid) for cid in group["member_ids"])
               if c is not None]
    members.sort(key=lambda c: (-_rank(c.risk_level), -(c.risk_score or 0)))

    dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for c in members:
        dist[c.risk_level] = dist.get(c.risk_level, 0) + 1

    peak = _peak([c.risk_level for c in members])
    peak_score = max((c.risk_score or 0 for c in members), default=0)

    drivers = []
    # Member drivers: the explainable factors behind each elevated relative.
    for c in members:
        if _rank(c.risk_level) < _HIGH:
            continue
        a = _latest_assessment(c)
        for f in (a.factors if a else None) or []:
            drivers.append({"source": "member", "customer_id": c.id,
                            "name": c.name, "level": c.risk_level,
                            "code": f.get("code"), "label": f.get("label"),
                            "impact": f.get("impact")})

    # Bridge actors + a group-level flag when the very link is a PEP.
    bridges = []
    for pid, b in group["bridges"].items():
        p = b["party"]
        connects = [{"customer_id": cc.id, "name": cc.name}
                    for cc in (Customer.query.get(cid) for cid in b["customers"])
                    if cc is not None]
        bridges.append({"party_id": pid, "name": p.name, "kind": p.kind,
                        "is_pep": bool(p.is_pep), "pep_type": p.pep_type,
                        "connects": connects})
        if p.is_pep:
            label = f"Shared controller {p.name} is a PEP"
            if p.pep_type:
                label += f" ({p.pep_type})"
            drivers.append({"source": "bridge", "party_id": pid, "name": p.name,
                            "level": "HIGH", "code": "SHARED_PEP",
                            "label": label, "impact": None})

    self_level = customer.risk_level
    return {
        "group_size": len(members),
        "peak_level": peak,
        "peak_score": peak_score,
        "self_level": self_level,
        "inherited": _rank(peak) > _rank(self_level),
        "distribution": dist,
        "members": [{"customer_id": c.id, "name": c.name,
                     "risk_level": c.risk_level, "risk_score": c.risk_score,
                     "is_self": c.id == customer.id} for c in members],
        "bridges": sorted(bridges, key=lambda x: (not x["is_pep"], x["name"])),
        "drivers": drivers,
    }
