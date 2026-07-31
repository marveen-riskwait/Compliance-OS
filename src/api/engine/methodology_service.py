"""Editable risk methodology — each organisation's own barème.

Instead of inheriting the system default, a compliance team can build its own
scoring model: weighted factors and the score bands that map to LOW / MEDIUM /
HIGH / CRITICAL. A methodology is edited only while DRAFT; activating it freezes
it (ACTIVE) and archives the previously active one, so every past RiskAssessment
stays interpretable under the exact version that produced it — an active or
archived methodology is never mutated in place.

`active` stays the single flag the risk engine queries; `status` layers the
DRAFT/ARCHIVED lifecycle on top (active == status ACTIVE).
"""
from api.models import db, RiskMethodology, RiskFactor, RiskThreshold
from api.models.risk import FACTOR_CONDITIONS
from api.engine import audit, risk_engine

LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]      # fixed severity ladder
# Customer boolean fields a FLAG factor may test.
FLAG_FIELDS = ("is_pep", "has_sanctions_match", "has_adverse_media",
               "complex_ownership")


class MethodologyError(ValueError):
    """Raised on any invalid edit; the route turns it into a 400."""


# --------------------------------------------------------------------------- #
# Guards
# --------------------------------------------------------------------------- #
def _owned_draft(m, organization_id):
    if m is None or m.organization_id != organization_id:
        raise MethodologyError("Methodology not found")
    if m.status != "DRAFT":
        raise MethodologyError("Only a draft methodology can be edited — "
                               "clone it to a new version to change it")
    return m


def _next_version(organization_id):
    n = RiskMethodology.query.filter_by(organization_id=organization_id).count()
    return f"org-v{n + 1}"


# --------------------------------------------------------------------------- #
# Methodology lifecycle
# --------------------------------------------------------------------------- #
def create_draft(organization_id, *, name=None, clone_from_id=None, actor=None):
    """New DRAFT for the org, cloning factors + thresholds from a source (an
    explicit methodology the org may read, else the org's active one, else the
    system default). Cloning guarantees a valid starting barème."""
    if clone_from_id:
        source = RiskMethodology.query.get(clone_from_id)
        if source is None or source.organization_id not in (None, organization_id):
            raise MethodologyError("Source methodology not found")
    else:
        source = risk_engine.active_methodology(organization_id)

    draft = RiskMethodology(
        organization_id=organization_id, version=_next_version(organization_id),
        name=(name or (f"{source.name} (copy)" if source else "New methodology")),
        active=False, status="DRAFT")
    db.session.add(draft)
    db.session.flush()

    if source:
        for f in source.factors:
            db.session.add(RiskFactor(
                methodology_id=draft.id, code=f.code, label=f.label,
                impact=f.impact, condition_type=f.condition_type,
                condition_value=f.condition_value, active=f.active))
        for t in source.thresholds:
            db.session.add(RiskThreshold(
                methodology_id=draft.id, level=t.level,
                min_score=t.min_score, max_score=t.max_score))
    else:
        for level, lo, hi in zip(LEVELS, (0, 31, 71, 101), (30, 70, 100, None)):
            db.session.add(RiskThreshold(methodology_id=draft.id, level=level,
                                         min_score=lo, max_score=hi))

    audit.record("RISK_METHODOLOGY_CREATED", "risk_methodology", draft.id,
                 actor=actor, new_value=f"{draft.name} ({draft.version})")
    db.session.commit()
    return draft


def rename_draft(organization_id, mid, name, actor=None):
    m = _owned_draft(RiskMethodology.query.get(mid), organization_id)
    new = (name or "").strip()[:120]
    if not new:
        raise MethodologyError("Name is required")
    m.name = new
    audit.record("RISK_METHODOLOGY_RENAMED", "risk_methodology", m.id,
                 actor=actor, new_value=m.name)
    db.session.commit()
    return m


def delete_draft(organization_id, mid, actor=None):
    m = _owned_draft(RiskMethodology.query.get(mid), organization_id)
    RiskFactor.query.filter_by(methodology_id=m.id).delete()
    RiskThreshold.query.filter_by(methodology_id=m.id).delete()
    db.session.delete(m)
    audit.record("RISK_METHODOLOGY_DELETED", "risk_methodology", mid, actor=actor)
    db.session.commit()


# --------------------------------------------------------------------------- #
# Factors
# --------------------------------------------------------------------------- #
def _clean_factor(code, label, impact, condition_type, condition_value):
    code = (code or "").strip().upper().replace(" ", "_")
    if not code:
        raise MethodologyError("Factor code is required")
    if not (label or "").strip():
        raise MethodologyError("Factor label is required")
    try:
        impact = int(impact)
    except (TypeError, ValueError):
        raise MethodologyError("Impact must be a whole number")
    if condition_type not in FACTOR_CONDITIONS:
        raise MethodologyError(f"Unknown condition type '{condition_type}'")
    cv = condition_value or {}
    if condition_type == "FLAG":
        field = cv.get("field")
        if field not in FLAG_FIELDS:
            raise MethodologyError(
                "A FLAG factor must test one of: " + ", ".join(FLAG_FIELDS))
        cv = {"field": field}
    else:                                   # COUNTRY_IN / ACTIVITY_IN
        values = [str(v).strip() for v in (cv.get("values") or []) if str(v).strip()]
        if not values:
            raise MethodologyError("Provide at least one value for this factor")
        cv = {"values": values}
    return code, label.strip()[:160], impact, condition_type, cv


def add_factor(organization_id, mid, data, actor=None):
    m = _owned_draft(RiskMethodology.query.get(mid), organization_id)
    code, label, impact, ct, cv = _clean_factor(
        data.get("code"), data.get("label"), data.get("impact"),
        data.get("condition_type"), data.get("condition_value"))
    f = RiskFactor(methodology_id=m.id, code=code, label=label, impact=impact,
                   condition_type=ct, condition_value=cv,
                   active=bool(data.get("active", True)))
    db.session.add(f)
    audit.record("RISK_FACTOR_ADDED", "risk_methodology", m.id, actor=actor,
                 new_value=f"{code} (+{impact})")
    db.session.commit()
    return f


def update_factor(organization_id, fid, data, actor=None):
    f = RiskFactor.query.get(fid)
    if f is None:
        raise MethodologyError("Factor not found")
    m = _owned_draft(f.methodology, organization_id)
    code, label, impact, ct, cv = _clean_factor(
        data.get("code", f.code), data.get("label", f.label),
        data.get("impact", f.impact),
        data.get("condition_type", f.condition_type),
        data.get("condition_value", f.condition_value))
    f.code, f.label, f.impact, f.condition_type, f.condition_value = \
        code, label, impact, ct, cv
    if "active" in data:
        f.active = bool(data["active"])
    audit.record("RISK_FACTOR_UPDATED", "risk_methodology", m.id, actor=actor,
                 new_value=f"{code} (+{impact})")
    db.session.commit()
    return f


def delete_factor(organization_id, fid, actor=None):
    f = RiskFactor.query.get(fid)
    if f is None:
        raise MethodologyError("Factor not found")
    m = _owned_draft(f.methodology, organization_id)
    db.session.delete(f)
    audit.record("RISK_FACTOR_REMOVED", "risk_methodology", m.id, actor=actor,
                 old_value=f.code)
    db.session.commit()


# --------------------------------------------------------------------------- #
# Thresholds — the band set must fully cover 0..∞ with no gap or overlap.
# --------------------------------------------------------------------------- #
def _validate_ladder(bands):
    by_level = {}
    for b in bands or []:
        lvl = (b.get("level") or "").upper()
        if lvl not in LEVELS:
            raise MethodologyError(f"Unknown level '{lvl}'")
        try:
            lo = int(b.get("min_score"))
        except (TypeError, ValueError):
            raise MethodologyError(f"{lvl}: min score must be a whole number")
        hi = b.get("max_score")
        hi = None if hi in (None, "") else int(hi)
        by_level[lvl] = (lo, hi)

    missing = [l for l in LEVELS if l not in by_level]
    if missing:
        raise MethodologyError("A band is required for: " + ", ".join(missing))

    ladder = [(l, *by_level[l]) for l in LEVELS]
    if ladder[0][1] != 0:
        raise MethodologyError("The lowest band (LOW) must start at 0")
    for i, (lvl, lo, hi) in enumerate(ladder):
        last = i == len(ladder) - 1
        if last:
            if hi is not None:
                raise MethodologyError(
                    f"The top band ({lvl}) must be open-ended (leave its max empty)")
            continue
        if hi is None:
            raise MethodologyError(f"Only the top band may be open-ended, not {lvl}")
        if hi < lo:
            raise MethodologyError(f"{lvl}: max must be greater than or equal to min")
        nlvl, nlo, _ = ladder[i + 1]
        if nlo != hi + 1:
            raise MethodologyError(
                f"Gap or overlap between {lvl} and {nlvl}: "
                f"{nlvl} must start at {hi + 1}")
    return ladder


def set_thresholds(organization_id, mid, bands, actor=None):
    m = _owned_draft(RiskMethodology.query.get(mid), organization_id)
    ladder = _validate_ladder(bands)
    RiskThreshold.query.filter_by(methodology_id=m.id).delete()
    for lvl, lo, hi in ladder:
        db.session.add(RiskThreshold(methodology_id=m.id, level=lvl,
                                     min_score=lo, max_score=hi))
    audit.record("RISK_THRESHOLDS_SET", "risk_methodology", m.id, actor=actor,
                 new_value="; ".join(f"{l} {lo}-{'∞' if hi is None else hi}"
                                     for l, lo, hi in ladder))
    db.session.commit()
    return m


# --------------------------------------------------------------------------- #
# Activation
# --------------------------------------------------------------------------- #
def activate(organization_id, mid, actor=None):
    """Make the draft the org's live methodology and archive the previous one.
    Validates the barème is usable first (≥1 active factor, valid bands)."""
    m = RiskMethodology.query.get(mid)
    if m is None or m.organization_id != organization_id:
        raise MethodologyError("Methodology not found")
    if m.status != "DRAFT":
        raise MethodologyError("Only a draft can be activated")
    if not any(f.active for f in m.factors):
        raise MethodologyError("Add at least one active factor before activating")
    _validate_ladder([t.serialize() for t in m.thresholds])   # raises if invalid

    for prev in (RiskMethodology.query
                 .filter_by(organization_id=organization_id, active=True).all()):
        prev.active = False
        prev.status = "ARCHIVED"
    m.active = True
    m.status = "ACTIVE"
    audit.record("RISK_METHODOLOGY_ACTIVATED", "risk_methodology", m.id,
                 actor=actor, new_value=f"{m.name} ({m.version})")
    db.session.commit()
    return m
