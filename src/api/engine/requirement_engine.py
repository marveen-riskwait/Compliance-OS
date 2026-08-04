"""Requirement engine — what a customer must provide, and what's still missing.

    Customer profile (type / risk / jurisdiction)
        -> applicable RequirementDefinitions
        -> compare with received data (ProfileField) + documents (Document)
        -> RequirementInstance status + completeness %
        -> (on request) Task / Notification + MISSING_INFORMATION_DETECTED

Computed BEFORE the consultant opens the review — the document's key
time-saving feature.
"""
from datetime import timedelta

from api.models import (
    db, Customer, Document, Party, ProfileField, RequirementDefinition,
    RequirementInstance, Task, RISK_RANK, utcnow,
)
from api.engine import audit
from api.engine.events import emit_event, recipients_for, notify_users


def applicable_definitions(customer):
    """System (org-null) + this org's definitions that apply to the customer."""
    rank = RISK_RANK.get(customer.risk_level, 0)
    defs = (RequirementDefinition.query
            .filter(RequirementDefinition.active.is_(True))
            .filter((RequirementDefinition.organization_id == customer.organization_id) |
                    (RequirementDefinition.organization_id.is_(None)))
            .all())
    out = []
    for d in defs:
        if d.applies_customer_type != "ANY" and d.applies_customer_type != customer.customer_type:
            continue
        # Scoped to specific company legal forms? Skip unless the customer's form
        # is one of them. A NULL/empty scope applies to every form of the type —
        # so a listed company, absent from the UBO-heavy rows, gets a lighter list.
        if d.applies_legal_form:
            forms = {s.strip() for s in d.applies_legal_form.split(",") if s.strip()}
            if (customer.legal_form or "") not in forms:
                continue
        if rank < (d.min_risk_rank or 0):
            continue
        if d.jurisdiction and d.jurisdiction != (customer.country or ""):
            continue
        out.append(d)
    return out


def _relevant_parties(customer):
    """Parties that each need their own identity documents: the UBOs and the
    control persons (SMOs) of the customer. Derived from the ownership graph, so
    the per-party checklist stays in step with who is actually on the file."""
    from api.engine import ownership
    return [u["party"] for u in ownership.compute_ubos(customer) if u.get("is_ubo")]


def _status_for(customer, d, party_id=None):
    if d.kind == "DATA":
        f = (ProfileField.query
             .filter_by(customer_id=customer.id, field_key=d.data_field).first())
        if f is None or f.value in (None, ""):
            return "MISSING"
        return "VERIFIED" if f.verified else "RECEIVED"
    # DOCUMENT — a row without a file is a document we are still waiting for,
    # not evidence. Counting it would inflate completeness against nothing. For a
    # per-party requirement only that party's own documents count.
    q = Document.query.filter_by(customer_id=customer.id, doc_type=d.doc_type)
    if party_id is not None:
        q = q.filter_by(party_id=party_id)
    with_file = [doc for doc in q.all() if doc.file_url]
    if not with_file:
        return "MISSING"
    if any(doc.status == "VERIFIED" for doc in with_file):
        return "VERIFIED"
    return "RECEIVED"


def evaluate(customer):
    """Recompute RequirementInstances for the customer; returns the instances.

    A per-party requirement expands into one instance per UBO/SMO, so a passport
    is tracked for each of them individually. Instances are keyed by
    (code, party_id) — a customer-level requirement uses party_id None."""
    applicable = applicable_definitions(customer)
    parties = _relevant_parties(customer)

    # Target set: (definition, party-or-None). A per-party definition with no
    # relevant parties yet produces nothing — we can't ask for a UBO's passport
    # before a UBO is on the file.
    targets = []
    for d in applicable:
        if d.per_party:
            targets += [(d, p) for p in parties]
        else:
            targets.append((d, None))

    existing = {(ri.code, ri.party_id): ri for ri in
                RequirementInstance.query.filter_by(customer_id=customer.id).all()}
    wanted = set()

    for d, p in targets:
        pid = p["id"] if p else None
        key = (d.code, pid)
        wanted.add(key)
        ri = existing.get(key)
        if ri is not None and ri.status == "WAIVED":
            continue  # a human waiver stands
        if ri is None:
            ri = RequirementInstance(customer_id=customer.id, code=d.code,
                                     kind=d.kind, party_id=pid)
            db.session.add(ri)
        ri.definition_id = d.id
        ri.kind = d.kind
        ri.label = f"{d.label} — {p['name']}" if p else d.label
        ri.status = _status_for(customer, d, party_id=pid)

    # Drop instances that no longer apply (unless explicitly waived) — including
    # a per-party row for someone who is no longer a UBO.
    for key, ri in existing.items():
        if key not in wanted and ri.status != "WAIVED":
            db.session.delete(ri)

    db.session.commit()
    _close_satisfied_requests(customer)
    return (RequirementInstance.query.filter_by(customer_id=customer.id)
            .order_by(RequirementInstance.kind, RequirementInstance.code).all())


def _close_satisfied_requests(customer):
    """Close the information-request tasks whose item has arrived.

    The chain only ever fired forwards: something missing opened a task, and
    nothing closed it when the customer sent it in. The visible cost is not the
    stale row — it is an analyst chasing a client who already complied, which
    is the one mistake a compliance team cannot afford to make twice.
    """
    satisfied = {ri.code for ri in
                 RequirementInstance.query.filter_by(customer_id=customer.id).all()
                 if ri.status != "MISSING"}
    if not satisfied:
        return 0

    open_tasks = (Task.query
                  .filter_by(customer_id=customer.id,
                             task_type="INFORMATION_REQUEST")
                  .filter(Task.status != "DONE").all())
    closed = 0
    for task in open_tasks:
        code = task.requirement_code
        if code is None:                       # tasks created before the link
            code = next((c for c in satisfied if f"({c})" in (task.title or "")), None)
        if code and code in satisfied:
            task.status = "DONE"
            audit.record("TASK_COMPLETED", "task", task.id,
                         new_value="DONE",
                         reason=f"{code} was provided by the customer")
            closed += 1
    if closed:
        db.session.commit()
    return closed


def _enriched(instances):
    """Serialize instances, adding the doc_type (for a per-party upload) and the
    party name — the label already carries it, but the id/name pair lets the UI
    group per-party requirements under each beneficial owner."""
    def_ids = {ri.definition_id for ri in instances if ri.definition_id}
    defs = ({d.id: d for d in RequirementDefinition.query
             .filter(RequirementDefinition.id.in_(def_ids)).all()}
            if def_ids else {})
    party_ids = {ri.party_id for ri in instances if ri.party_id}
    parties = ({p.id: p for p in Party.query.filter(Party.id.in_(party_ids)).all()}
               if party_ids else {})
    out = []
    for ri in instances:
        data = ri.serialize()
        d = defs.get(ri.definition_id)
        data["doc_type"] = d.doc_type if d else None
        data["per_party"] = bool(d and d.per_party)
        data["party_name"] = parties[ri.party_id].name if ri.party_id in parties else None
        out.append(data)
    return out


def summary(customer):
    instances = evaluate(customer)
    total = len(instances) or 1
    satisfied = sum(1 for ri in instances if ri.status in ("VERIFIED", "RECEIVED", "WAIVED"))
    missing = [ri for ri in instances if ri.status == "MISSING"]
    return {
        "completeness_pct": round(100 * satisfied / total),
        "total": len(instances),
        "satisfied": satisfied,
        "missing_count": len(missing),
        "missing": _enriched(missing),
        "requirements": _enriched(instances),
    }


def _notify_customer_portal(customer):
    """Best effort: tell the customer something is waiting, nothing more."""
    try:
        from api.portal import notify_customer
        notify_customer(customer, what="some information")
    except Exception:
        pass          # a mail problem must never fail a compliance action


def request_missing_info(customer, actor=None):
    """Create one information-request task per missing requirement, notify the
    responsible team, and emit MISSING_INFORMATION_DETECTED once."""
    instances = evaluate(customer)
    missing = [ri for ri in instances if ri.status == "MISSING"]
    if not missing:
        return {"created": 0, "missing": 0}

    created = 0
    for ri in missing:
        exists = (Task.query.filter_by(customer_id=customer.id,
                                       task_type="INFORMATION_REQUEST")
                  .filter(db.or_(Task.requirement_code == ri.code,
                                 Task.title.like(f"%{ri.code}%")))
                  .filter(Task.status != "DONE").first())
        if exists:
            continue
        db.session.add(Task(
            customer_id=customer.id,
            task_type="INFORMATION_REQUEST",
            title=f"Request missing: {ri.label} ({ri.code})",
            requirement_code=ri.code,
            priority="MEDIUM",
            due_at=utcnow() + timedelta(days=10),
        ))
        created += 1

    users = recipients_for(customer, ["ANALYST", "KYC_ANALYST"])
    notify_users(users, severity="MEDIUM",
                 title="Missing information",
                 message=f"{len(missing)} requirement(s) missing for {customer.name}.",
                 customer_id=customer.id, requires_action=True)
    audit.record("INFORMATION_REQUESTED", "customer", customer.id, actor=actor,
                 new_value=", ".join(ri.code for ri in missing))
    db.session.commit()

    emit_event("MISSING_INFORMATION_DETECTED", customer_id=customer.id,
               severity="MEDIUM", source="requirement_engine", actor=actor,
               payload={"missing": [ri.code for ri in missing]})
    # The team now has tasks; the customer needs to know something is waiting.
    _notify_customer_portal(customer)
    return {"created": created, "missing": len(missing)}
