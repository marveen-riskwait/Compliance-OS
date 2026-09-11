"""Recode stored free-text countries / activities to catalogue codes.

Idempotent and best-effort: values the catalogue does not recognise are left
exactly as they are. Used by the a1c2e3f4b5d6 migration and by the
`flask recode-catalogues` command (run it again after extending the aliases,
or on a database that was migrated before an alias existed).
"""
import json

import sqlalchemy as sa

from api.catalogues.countries import to_iso2
from api.catalogues.activities import to_activity_code

COUNTRY_COLUMNS = [
    ("customer", "country"),
    ("party", "nationality"), ("party", "country_of_residence"), ("party", "country_of_incorporation"),
    ("address", "country"),
    ("transaction", "counterparty_country"),
]
COUNTRY_FIELD_KEYS = ("country_of_birth", "nationality", "country_of_tax_residence",
                      "residential_country", "country_of_incorporation", "governing_law",
                      "pep_country", "principal_place_of_business_country")
GEO_FIELDS = ["country", "residence", "nationality", "incorporation", "principal_place_of_business"]


def _q(name):
    return f'"{name}"'


def recode_all(bind):
    """Returns {"recoded": n, "left": [(table.column, value), ...]}."""
    recoded, left = 0, []
    for table, col in COUNTRY_COLUMNS:
        rows = bind.execute(sa.text(
            f"SELECT id, {_q(col)} AS v FROM {_q(table)} WHERE {_q(col)} IS NOT NULL AND {_q(col)} != ''")).fetchall()
        for rid, v in rows:
            code = to_iso2(v)
            if code and code != v:
                bind.execute(sa.text(f"UPDATE {_q(table)} SET {_q(col)} = :c WHERE id = :i"), {"c": code, "i": rid})
                recoded += 1
            elif not code:
                left.append((f"{table}.{col}", v))
    rows = bind.execute(sa.text(
        "SELECT id, field_key, value FROM profile_field WHERE field_key IN :keys AND value IS NOT NULL AND value != ''"
        ).bindparams(sa.bindparam("keys", expanding=True)), {"keys": list(COUNTRY_FIELD_KEYS)}).fetchall()
    for rid, key, v in rows:
        code = to_iso2(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE profile_field SET value = :c WHERE id = :i"), {"c": code, "i": rid})
            recoded += 1
        elif not code:
            left.append((f"profile_field.{key}", v))
    rows = bind.execute(sa.text(
        "SELECT id, business_activity, business_activity_detail FROM customer WHERE business_activity IS NOT NULL AND business_activity != ''")).fetchall()
    for rid, v, detail in rows:
        code = to_activity_code(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE customer SET business_activity = :c, business_activity_detail = COALESCE(business_activity_detail, :d) WHERE id = :i"),
                         {"c": code, "d": v, "i": rid})
            recoded += 1
        elif not code:
            left.append(("customer.business_activity", v))
    for table in ("party",):
        rows = bind.execute(sa.text(
            f"SELECT id, business_activity FROM {table} WHERE business_activity IS NOT NULL AND business_activity != ''")).fetchall()
        for rid, v in rows:
            code = to_activity_code(v)
            if code and code != v:
                bind.execute(sa.text(f"UPDATE {table} SET business_activity = :c WHERE id = :i"), {"c": code, "i": rid})
                recoded += 1
    rows = bind.execute(sa.text(
        "SELECT id, value FROM profile_field WHERE field_key = 'business_activity' AND value IS NOT NULL AND value != ''")).fetchall()
    for rid, v in rows:
        code = to_activity_code(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE profile_field SET value = :c WHERE id = :i"), {"c": code, "i": rid})
            recoded += 1
    rows = bind.execute(sa.text(
        "SELECT id, code, condition_type, condition_value FROM risk_factor WHERE condition_type IN ('COUNTRY_IN','ACTIVITY_IN')")).fetchall()
    for rid, fcode, ctype, cv in rows:
        try:
            data = json.loads(cv) if isinstance(cv, str) else (cv or {})
        except ValueError:
            continue
        values = data.get("values") or []
        if ctype == "COUNTRY_IN":
            new_values = sorted({to_iso2(v) or v for v in values})
            if fcode.startswith("GEO_") and not data.get("fields"):
                data["fields"] = GEO_FIELDS
        else:
            new_values = sorted({to_activity_code(v) or v for v in values})
        if new_values != values or (fcode.startswith("GEO_") and ctype == "COUNTRY_IN" and data.get("fields") == GEO_FIELDS and "fields" not in (json.loads(cv) if isinstance(cv, str) else (cv or {}))):
            data["values"] = new_values
            bind.execute(sa.text("UPDATE risk_factor SET condition_value = :v WHERE id = :i"),
                         {"v": json.dumps(data), "i": rid})
            recoded += 1
    return {"recoded": recoded, "left": left}
