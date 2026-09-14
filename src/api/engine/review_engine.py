"""Review engine — scheduled + event-driven customer reviews.

Review frequency follows risk (LOW 36m ... CRITICAL 6m), but a review is also
triggered immediately by material events (PEP, sanctions, UBO change, adverse
media). Continuous monitoring flips SCHEDULED -> DUE and DUE -> OVERDUE.
"""
from datetime import timedelta

from api.models import (
    db, Customer, Review, REVIEW_FREQUENCY_MONTHS, utcnow,
)
from api.engine import audit
from api.engine.events import emit_event

# Events that trigger an immediate event-driven review.
REVIEW_TRIGGERS = {"PEP_DETECTED", "SANCTIONS_MATCH_FOUND", "UBO_CHANGED",
                   "ADVERSE_MEDIA_DETECTED"}


def frequency_months(risk_level):
    return REVIEW_FREQUENCY_MONTHS.get(risk_level, 24)


def _open_reviews(customer_id):
    return Review.query.filter_by(customer_id=customer_id).filter(
        Review.status.in_(["SCHEDULED", "DUE", "IN_PROGRESS", "OVERDUE"]))


def schedule_initial(customer, actor=None):
    """On onboarding: an INITIAL_KYC review is due now."""
    review = Review(organization_id=customer.organization_id,
                    customer_id=customer.id, review_type="INITIAL_KYC",
                    status="DUE", trigger="Onboarding",
                    due_at=utcnow() + timedelta(days=30))
    db.session.add(review)
    audit.record("REVIEW_SCHEDULED", "review", None, actor=actor,
                 new_value="INITIAL_KYC", reason="onboarding", commit=True)
    return review


def create_event_driven(customer, trigger, actor=None):
    """Immediate review triggered by an event (deduped by trigger)."""
    exists = _open_reviews(customer.id).filter(
        Review.review_type == "EVENT_DRIVEN_REVIEW",
        Review.trigger == trigger).first()
    if exists:
        return exists
    review = Review(organization_id=customer.organization_id,
                    customer_id=customer.id, review_type="EVENT_DRIVEN_REVIEW",
                    status="DUE", trigger=trigger,
                    due_at=utcnow() + timedelta(days=5))
    db.session.add(review)
    audit.record("REVIEW_SCHEDULED", "review", None, actor=actor,
                 new_value="EVENT_DRIVEN_REVIEW", reason=trigger, commit=True)
    return review


def maybe_event_review(event):
    if event.event_type in REVIEW_TRIGGERS and event.customer_id:
        customer = Customer.query.get(event.customer_id)
        if customer:
            create_event_driven(customer, trigger=event.event_type)


def complete_review(review, decision, reason, actor=None):
    review.status = "COMPLETED"
    review.completed_at = utcnow()
    review.decision = decision
    review.decision_reason = reason
    customer = Customer.query.get(review.customer_id)
    customer.last_review_at = utcnow()
    # An approved initial KYC is what turns an onboarding file into an active
    # relationship; a rejection leaves it in onboarding for remediation.
    if review.review_type == "INITIAL_KYC" and customer.status in ("ONBOARDING", "SUBMITTED"):
        if (decision or "").upper() == "APPROVED":
            customer.status = "ACTIVE"
    audit.record("REVIEW_COMPLETED", "review", review.id, actor=actor,
                 new_value=decision, reason=reason)

    # Schedule the next periodic review by current risk.
    months = frequency_months(customer.risk_level)
    scheduled_for = utcnow() + timedelta(days=months * 30)
    nxt = Review(organization_id=customer.organization_id,
                 customer_id=customer.id, review_type="PERIODIC_REVIEW",
                 status="SCHEDULED", trigger=f"Every {months} months ({customer.risk_level})",
                 scheduled_for=scheduled_for,
                 due_at=scheduled_for + timedelta(days=30))
    db.session.add(nxt)
    db.session.commit()
    return review, nxt


ONBOARDING_LABELS = {
    "NOT_STARTED": "Onboarding — not started",
    "PENDING_REVIEW": "Onboarding — awaiting review",
    "SUBMITTED": "Onboarding — submitted by the customer, awaiting review",
    "IN_REVIEW": "Onboarding — under review",
    "APPROVED": "Onboarded",
    "REJECTED": "Onboarding — rejected, remediation needed",
    "ARCHIVED": "Archived",
}


def onboarding_summaries(customers):
    """{customer_id: {"onboarding": {...}, "valid_until": iso|None}} for a
    list of customers in two queries — cheap enough for the book view.

    The onboarding state is derived from the INITIAL_KYC review (there is no
    separate approval object); "valid until" is the date the next periodic
    review is scheduled — the file is considered current until then."""
    ids = [c.id for c in customers]
    if not ids:
        return {}
    initial = {}
    for r in (Review.query.filter(Review.customer_id.in_(ids),
                                  Review.review_type == "INITIAL_KYC")
              .order_by(Review.created_at.desc()).all()):
        initial.setdefault(r.customer_id, r)          # newest first
    nxt = {}
    for r in (Review.query.filter(Review.customer_id.in_(ids),
                                  Review.review_type == "PERIODIC_REVIEW",
                                  Review.status.in_(["SCHEDULED", "DUE", "OVERDUE", "IN_PROGRESS"]))
              .order_by(Review.scheduled_for.asc(), Review.due_at.asc()).all()):
        nxt.setdefault(r.customer_id, r)              # earliest first
    now = utcnow()
    out = {}
    for c in customers:
        r = initial.get(c.id)
        if c.status == "ARCHIVED":
            state = "ARCHIVED"
        elif r is None:
            state = "NOT_STARTED"
        elif r.status == "COMPLETED":
            state = "APPROVED" if (r.decision or "").upper() == "APPROVED" else "REJECTED"
        elif r.status == "IN_PROGRESS":
            state = "IN_REVIEW"
        else:
            state = "SUBMITTED" if c.status == "SUBMITTED" else "PENDING_REVIEW"
        n = nxt.get(c.id)
        valid_until = None
        lapsed = False
        if state == "APPROVED" and n is not None:
            valid_until = n.scheduled_for or n.due_at
            lapsed = n.status == "OVERDUE" or (n.due_at is not None and n.due_at < now)
        out[c.id] = {
            "onboarding": {
                "state": state,
                "label": ONBOARDING_LABELS.get(state, state),
                "review_id": r.id if r else None,
                "review_status": r.status if r else None,
                "decided_at": r.completed_at.isoformat() if (r and r.completed_at) else None,
                "due_at": r.due_at.isoformat() if (r and r.due_at and r.status != "COMPLETED") else None,
            },
            "valid_until": valid_until.isoformat() if valid_until else None,
            "validity_lapsed": lapsed,
        }
    return out


def onboarding_summary(customer):
    return onboarding_summaries([customer]).get(customer.id)


OPEN_MATCH_STATUSES = ("POTENTIAL", "UNDER_REVIEW", "ESCALATED")


def approval_blockers(customer):
    """What must be in place before an approval is recorded on a review —
    the analyst can still approve, but only by naming why (audited)."""
    from api.engine import requirement_engine
    from api.models import ScreeningRun, ScreeningMatch
    out = []
    s = requirement_engine.summary(customer)
    if s.get("missing_count"):
        names = [(m.get("label") or m.get("code") or "?") for m in (s.get("missing") or [])[:5]]
        out.append({"code": "MISSING_REQUIREMENTS",
                    "message": f"{s['missing_count']} mandatory item(s) still missing: "
                               + ", ".join(names) + ("…" if s["missing_count"] > 5 else "")})
    if ScreeningRun.query.filter_by(customer_id=customer.id).count() == 0:
        out.append({"code": "SCREENING_NOT_RUN",
                    "message": "Screening has never been run on this file"})
    open_matches = (ScreeningMatch.query.filter_by(customer_id=customer.id)
                    .filter(ScreeningMatch.status.in_(OPEN_MATCH_STATUSES)).count())
    if open_matches:
        out.append({"code": "OPEN_MATCHES",
                    "message": f"{open_matches} screening match(es) not yet decided (confirm or clear them)"})
    return out


def start_review(review, actor=None):
    review.status = "IN_PROGRESS"
    review.started_at = utcnow()
    review.assigned_to = actor.id if actor else review.assigned_to
    db.session.commit()
    return review


def run_monitoring():
    """Flip SCHEDULED->DUE and DUE/IN_PROGRESS->OVERDUE; emit events. Returns counts."""
    now = utcnow()
    became_due = 0
    for r in Review.query.filter_by(status="SCHEDULED").filter(
            Review.scheduled_for.isnot(None)).filter(Review.scheduled_for <= now).all():
        r.status = "DUE"
        db.session.commit()
        emit_event("REVIEW_DUE", customer_id=r.customer_id, severity="MEDIUM",
                   source="monitoring", payload={"review_id": r.id, "type": r.review_type})
        became_due += 1

    became_overdue = 0
    for r in Review.query.filter(Review.status.in_(["DUE", "IN_PROGRESS"])).filter(
            Review.due_at.isnot(None)).filter(Review.due_at < now).all():
        r.status = "OVERDUE"
        db.session.commit()
        emit_event("REVIEW_OVERDUE", customer_id=r.customer_id, severity="HIGH",
                   source="monitoring", payload={"review_id": r.id, "type": r.review_type})
        became_overdue += 1

    return {"became_due": became_due, "became_overdue": became_overdue}
