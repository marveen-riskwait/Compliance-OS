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
from api.models import Customer, Party, Transaction
from api.engine import ownership
from api.engine.party_service import party_links, _name_ratio, _norm

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


# --------------------------------------------------------------------------- #
# Linked transactional flows — money moving BETWEEN members of the same group.
# Per-customer monitoring sees each leg in isolation; only at the group level do
# intra-group transfers, round-trips and layering between related entities show
# up. A counterparty is matched (fuzzily) to a sister member by name.
# --------------------------------------------------------------------------- #
_FLOW_MATCH_MIN = 0.85


def _match_member(counterparty, members, exclude_id):
    """Best sister member whose name matches this counterparty (or None)."""
    cp = _norm(counterparty)
    if not cp:
        return None
    best_id, best = None, 0.0
    for oid, oc in members.items():
        if oid == exclude_id:
            continue
        nm = _norm(oc.name)
        score = _name_ratio(counterparty, oc.name)
        if nm and nm in cp:              # counterparty text contains the member name
            score = max(score, 0.95)
        if score > best:
            best_id, best = oid, score
    return best_id if best >= _FLOW_MATCH_MIN else None


def group_flows(customer):
    """Directed money flows between members of the customer's economic group.
    Each booked transaction whose counterparty resolves to a sister member
    becomes an edge (payer -> payee, by its own direction); edges are aggregated
    per pair with amount, count, how many legs were flagged, and a round_trip
    marker when money also flows back. Amounts are as-booked in the reporting
    currency — mirror legs booked on both sides are not reconciled (a later
    refinement, like FX normalisation)."""
    group = build_group(customer)
    members = {c.id: c for c in
               (Customer.query.get(cid) for cid in group["member_ids"])
               if c is not None}

    flows = {}      # (src_id, dst_id) -> aggregate
    for cid, c in members.items():
        for t in Transaction.query.filter_by(customer_id=cid).all():
            other = _match_member(t.counterparty_name, members, cid)
            if other is None:
                continue
            src, dst = (cid, other) if t.direction == "OUTBOUND" else (other, cid)
            f = flows.setdefault((src, dst), {
                "source_id": src, "target_id": dst,
                "amount_base": 0.0, "count": 0, "flagged": 0})
            f["amount_base"] += (t.amount_base or 0)
            f["count"] += 1
            if t.flagged:
                f["flagged"] += 1

    edges = []
    for (src, dst), f in flows.items():
        edges.append({**f,
                      "source_name": members[src].name,
                      "target_name": members[dst].name,
                      "round_trip": (dst, src) in flows})
    edges.sort(key=lambda e: -e["amount_base"])
    return {"group_size": len(members),
            "total_base": round(sum(e["amount_base"] for e in edges), 2),
            "flagged_flows": sum(1 for e in edges if e["flagged"]),
            "round_trips": sum(1 for e in edges if e["round_trip"]) // 2,
            "flows": edges}
