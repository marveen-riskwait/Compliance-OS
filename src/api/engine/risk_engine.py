"""Risk Engine — explainable, versioned, data-driven risk scoring.

The active RiskMethodology (its factors + thresholds) lives in the database and
is versioned; every recompute stores the exact factors that produced the score,
the required actions and the methodology version, as a new RiskAssessment row so
the history stays auditable and interpretable under the methodology used.

If no methodology is configured, a legacy hardcoded set is used as a fallback so
the platform always scores risk.
"""
from api.models import (
    db, Customer, RiskAssessment, RiskMethodology,
    HIGH_RISK_COUNTRIES, HIGH_RISK_ACTIVITIES,
)
from api.engine import audit
from api.catalogues import to_iso2, to_activity_code

# --- Legacy fallback (used only when no methodology exists in the DB) --------
_LEGACY_FACTORS = [
    (lambda c: c.is_pep, "PEP", "Politically Exposed Person detected", 30),
    (lambda c: c.has_sanctions_match, "SANCTIONS", "Potential sanctions match", 40),
    (lambda c: c.has_adverse_media, "ADVERSE_MEDIA", "Relevant adverse media", 20),
    (lambda c: c.complex_ownership, "OWNERSHIP", "Complex ownership structure", 15),
    (lambda c: to_iso2(c.country) in HIGH_RISK_COUNTRIES,
     "GEOGRAPHY", "High-risk jurisdiction", 20),
    (lambda c: to_activity_code(c.business_activity) in HIGH_RISK_ACTIVITIES,
     "BUSINESS", "High-risk business activity", 25),
]
_LEGACY_THRESHOLDS = [("LOW", 0, 30), ("MEDIUM", 31, 70),
                      ("HIGH", 71, 100), ("CRITICAL", 101, None)]


def active_methodology(organization_id):
    """Prefer the organization's active methodology, else a shared/system one."""
    org = (RiskMethodology.query
           .filter_by(organization_id=organization_id, active=True).first())
    if org:
        return org
    return (RiskMethodology.query
            .filter_by(organization_id=None, active=True).first())


def _country_values(customer):
    """Every country recorded on the file, by role. Codes (ISO alpha-2) when
    recognised, else the raw text — so a legacy free-text value still has a
    chance to match a legacy free-text list."""
    from api.models import ProfileField
    out = {"country": customer.country}
    root = None
    if getattr(customer, "root_party_id", None):
        from api.models import Party
        root = db.session.get(Party, customer.root_party_id)
    if root is not None:
        out["residence"] = getattr(root, "country_of_residence", None)
        out["nationality"] = getattr(root, "nationality", None)
        out["incorporation"] = getattr(root, "country_of_incorporation", None)
    keys = {"residential_country": "residence", "country_of_tax_residence": "residence",
            "nationality": "nationality", "country_of_incorporation": "incorporation",
            "principal_place_of_business_country": "principal_place_of_business"}
    if customer.id is not None:
        for f in ProfileField.query.filter(ProfileField.customer_id == customer.id,
                                           ProfileField.field_key.in_(list(keys))).all():
            role = keys[f.field_key]
            if f.value and not out.get(role):
                out[role] = f.value
    return {k: (to_iso2(v) or (v or "").strip().lower()) for k, v in out.items() if v}


def _factor_matches(factor, customer):
    """Falsy when the factor does not apply; otherwise a short string saying
    what matched (kept on the assessment so the score is explainable)."""
    ct = factor.condition_type
    cv = factor.condition_value or {}
    if ct == "FLAG":
        return cv.get("field") if getattr(customer, cv.get("field", ""), False) else None
    if ct == "COUNTRY_IN":
        wanted = {to_iso2(v) or str(v).strip().lower() for v in cv.get("values", [])}
        fields = cv.get("fields") or ["country"]
        have = _country_values(customer)
        for role in fields:
            val = have.get(role)
            if val and val in wanted:
                return f"{role}={val}"
        return None
    if ct == "ACTIVITY_IN":
        wanted = {to_activity_code(v) or str(v).strip().lower() for v in cv.get("values", [])}
        mine = to_activity_code(customer.business_activity) or (customer.business_activity or "").strip().lower()
        return f"activity={mine}" if mine and mine in wanted else None
    return None


def _level_from(thresholds, score):
    for level, lo, hi in sorted(thresholds, key=lambda t: t[1]):
        if score >= lo and (hi is None or score <= hi):
            return level
    return "LOW"


def _evaluate(customer):
    """Return (factors, score, level, methodology_version) using the DB
    methodology, or the legacy fallback."""
    methodology = active_methodology(customer.organization_id)
    factors, score = [], 0

    if methodology and methodology.factors:
        for f in methodology.factors:
            via = _factor_matches(f, customer) if f.active else None
            if via:
                score += f.impact
                factors.append({"code": f.code, "label": f.label, "impact": f.impact, "via": via})
        thresholds = [(t.level, t.min_score, t.max_score)
                      for t in methodology.thresholds] or _LEGACY_THRESHOLDS
        return factors, score, _level_from(thresholds, score), methodology.version

    for predicate, code, label, impact in _LEGACY_FACTORS:
        if predicate(customer):
            score += impact
            factors.append({"code": code, "label": label, "impact": impact})
    return factors, score, _level_from(_LEGACY_THRESHOLDS, score), "legacy-v1"


def _required_actions(level, factors):
    actions = []
    codes = {f["code"] for f in factors}
    if level in ("HIGH", "CRITICAL"):
        actions += ["Enhanced Due Diligence", "Source of Wealth",
                    "Source of Funds", "Senior management approval"]
    if "PEP" in codes:
        actions.append("PEP periodic monitoring")
    if "SANCTIONS" in codes:
        actions.append("Sanctions match investigation")
    review = {"LOW": "Review every 36 months", "MEDIUM": "Review every 24 months",
              "HIGH": "Review every 12 months", "CRITICAL": "Review every 3-6 months"}
    actions.append(review[level])
    seen, ordered = set(), []
    for a in actions:
        if a not in seen:
            seen.add(a)
            ordered.append(a)
    return ordered


def recompute(customer: Customer, *, actor=None, reason="Risk recomputed"):
    """Recompute risk for a customer, persist a new (versioned) assessment,
    update the denormalised fields and leave an audit trail.

    Does NOT emit further compliance events — callers own that decision to keep
    processing loop-free.
    """
    factors, score, level, version = _evaluate(customer)
    actions = _required_actions(level, factors)
    old_score, old_level = customer.risk_score, customer.risk_level

    assessment = RiskAssessment(
        customer_id=customer.id,
        score=score,
        level=level,
        methodology_version=version,
        factors=factors,
        required_actions=actions,
        reason=reason,
    )
    db.session.add(assessment)

    customer.risk_score = score
    customer.risk_level = level

    if old_score != score or old_level != level:
        audit.record(
            "RISK_UPDATED", "customer", customer.id, actor=actor,
            old_value=f"{old_level} ({old_score})",
            new_value=f"{level} ({score})", reason=reason)

    db.session.commit()
    return assessment
