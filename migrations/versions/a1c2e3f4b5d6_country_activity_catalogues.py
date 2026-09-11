"""Country codes (ISO 3166-1 alpha-2) and closed activity catalogue.

Revision ID: a1c2e3f4b5d6
Revises: d4a7e9c2f1b8
Create Date: 2026-09-11

Adds customer.business_activity_detail and recodes existing free-text
countries / activities to catalogue codes wherever the platform compares them
(customer, party, address, transaction, KYC profile fields, risk factors).
Values that fit no catalogue entry are left untouched — nothing a human typed
is dropped. The recoding is not reversed on downgrade (codes stay readable).
"""
import json
import sys
import os

from alembic import op
import sqlalchemy as sa

revision = "a1c2e3f4b5d6"
down_revision = "d4a7e9c2f1b8"
branch_labels = None
depends_on = None

# Make `api.catalogues` importable whether alembic runs from the repo root or src/.
_HERE = os.path.dirname(os.path.abspath(__file__))
for cand in (os.path.join(_HERE, "..", "..", "src"), os.path.join(_HERE, "..", "..")):
    cand = os.path.abspath(cand)
    if os.path.isdir(os.path.join(cand, "api")) and cand not in sys.path:
        sys.path.insert(0, cand)

COUNTRY_COLUMNS = [
    ("customer", "country"),
    ("party", "nationality"), ("party", "country_of_residence"), ("party", "country_of_incorporation"),
    ("address", "country"),
    ("transaction", "counterparty_country"),
]
COUNTRY_FIELD_KEYS = ("country_of_birth", "nationality", "country_of_tax_residence",
                      "residential_country", "country_of_incorporation", "governing_law",
                      "pep_country", "principal_place_of_business_country")


def _q(name):
    return f'"{name}"'


def upgrade():
    with op.batch_alter_table("customer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("business_activity_detail", sa.Text(), nullable=True))

    try:
        from api.catalogues.countries import to_iso2
        from api.catalogues.activities import to_activity_code
    except Exception as exc:  # pragma: no cover - defensive: schema first, data best-effort
        print(f"[a1c2e3f4b5d6] catalogue import failed ({exc}); skipping recoding")
        return

    bind = op.get_bind()
    recoded = 0
    # 1. Country columns
    for table, col in COUNTRY_COLUMNS:
        rows = bind.execute(sa.text(
            f"SELECT id, {_q(col)} AS v FROM {_q(table)} WHERE {_q(col)} IS NOT NULL AND {_q(col)} != ''")).fetchall()
        for rid, v in rows:
            code = to_iso2(v)
            if code and code != v:
                bind.execute(sa.text(f"UPDATE {_q(table)} SET {_q(col)} = :c WHERE id = :i"), {"c": code, "i": rid})
                recoded += 1
    # 2. KYC profile fields holding a country
    rows = bind.execute(sa.text(
        "SELECT id, value FROM profile_field WHERE field_key IN :keys AND value IS NOT NULL AND value != ''"
        ).bindparams(sa.bindparam("keys", expanding=True)), {"keys": list(COUNTRY_FIELD_KEYS)}).fetchall()
    for rid, v in rows:
        code = to_iso2(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE profile_field SET value = :c WHERE id = :i"), {"c": code, "i": rid})
            recoded += 1
    # 3. Business activity: code in the column, original text kept as detail
    rows = bind.execute(sa.text(
        "SELECT id, business_activity FROM customer WHERE business_activity IS NOT NULL AND business_activity != ''")).fetchall()
    for rid, v in rows:
        code = to_activity_code(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE customer SET business_activity = :c, business_activity_detail = :d WHERE id = :i"),
                         {"c": code, "d": v, "i": rid})
            recoded += 1
    rows = bind.execute(sa.text(
        "SELECT id, business_activity FROM party WHERE business_activity IS NOT NULL AND business_activity != ''")).fetchall()
    for rid, v in rows:
        code = to_activity_code(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE party SET business_activity = :c WHERE id = :i"), {"c": code, "i": rid})
            recoded += 1
    rows = bind.execute(sa.text(
        "SELECT id, value FROM profile_field WHERE field_key = 'business_activity' AND value IS NOT NULL AND value != ''")).fetchall()
    for rid, v in rows:
        code = to_activity_code(v)
        if code and code != v:
            bind.execute(sa.text("UPDATE profile_field SET value = :c WHERE id = :i"), {"c": code, "i": rid})
            recoded += 1
    # 4. Risk factor lists (JSON): values become codes; geography factors look at every country on the file
    geo_fields = ["country", "residence", "nationality", "incorporation", "principal_place_of_business"]
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
                data["fields"] = geo_fields
        else:
            new_values = sorted({to_activity_code(v) or v for v in values})
        if new_values != values or "fields" in data:
            data["values"] = new_values
            bind.execute(sa.text("UPDATE risk_factor SET condition_value = :v WHERE id = :i"),
                         {"v": json.dumps(data), "i": rid})
            recoded += 1
    print(f"[a1c2e3f4b5d6] recoded {recoded} value(s) to catalogue codes")


def downgrade():
    with op.batch_alter_table("customer", schema=None) as batch_op:
        batch_op.drop_column("business_activity_detail")
