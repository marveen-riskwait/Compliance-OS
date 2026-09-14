"""Reference data the platform compares against: countries (ISO 3166-1
alpha-2) and business activities (closed list mapped to NACE and to risk)."""
from api.catalogues import countries, activities  # noqa: F401
from api.catalogues.countries import to_iso2, country_name, is_iso2  # noqa: F401
from api.catalogues.activities import (to_activity_code, activity_label,  # noqa: F401
                                       activity_from_nace, HIGH_RISK_CODES as HIGH_RISK_ACTIVITY_CODES)

# KYC-form / profile-field keys whose value is a country.
COUNTRY_FIELD_KEYS = {
    "country_of_birth", "nationality", "country_of_tax_residence",
    "residential_country", "country_of_incorporation", "governing_law",
    "pep_country", "principal_place_of_business_country",
}


def normalise_form_value(key, spec, value):
    """Store catalogue codes for country-typed answers and for the business
    activity; leave everything else exactly as typed. Unknown values are kept
    verbatim (never silently dropped)."""
    import json as _json
    ftype = (spec or {}).get("type")
    if ftype == "contacts":
        # A JSON list of {name, title, email, phone}; empty rows are dropped.
        try:
            rows = _json.loads(value) if value else []
        except ValueError:
            raise ValueError("contact_persons must be a JSON list")
        clean = [{k: str(r.get(k) or "").strip()[:200] for k in ("name", "title", "email", "phone")}
                 for r in rows if isinstance(r, dict) and str(r.get("name") or "").strip()]
        return _json.dumps(clean, ensure_ascii=False) if clean else ""
    if ftype == "parties":
        return ",".join(sorted({x.strip() for x in str(value).split(",") if x.strip().isdigit()}, key=int))
    if value is None:
        return value
    s = str(value).strip()
    if not s:
        return s
    is_country = key in COUNTRY_FIELD_KEYS or (spec or {}).get("type") == "country"
    if is_country:
        return countries.to_iso2(s) or s
    if key == "business_activity":
        return activities.to_activity_code(s) or s
    return s


def catalogues():
    return {"countries": countries.catalogue(), "activities": activities.catalogue(),
            "nace_hint": "Enter a NACE Rev. 2 code (e.g. 64.19) to pre-select the activity."}
