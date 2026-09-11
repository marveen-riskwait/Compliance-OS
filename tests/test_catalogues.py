"""Countries are ISO alpha-2 codes and activities a closed catalogue — and the
risk engine matches on them regardless of how a value was typed."""
from api.catalogues.countries import to_iso2, country_name, same_country
from api.catalogues.activities import to_activity_code, activity_from_nace, activity_label
from api.models import db, Customer, RiskMethodology, RiskFactor
from api.engine import risk_engine
from conftest import auth


def test_country_normaliser_accepts_codes_names_and_aliases():
    assert to_iso2("IR") == "IR"
    assert to_iso2("iran") == "IR"
    assert to_iso2("Iran (Islamic Republic of)") == "IR"
    assert to_iso2("Korea, Democratic People's Republic of") == "KP"
    assert to_iso2("UK") == "GB" and to_iso2("United Kingdom") == "GB"
    assert to_iso2("US-DE") == "US"          # SEC EDGAR state of incorporation
    assert to_iso2("Narnia") is None and to_iso2("") is None and to_iso2(None) is None
    assert country_name("LU") == "Luxembourg" and country_name("free text") == "free text"
    assert same_country("Russia", "RU") and not same_country("RU", "FR")


def test_activity_catalogue_recodes_free_text_and_nace():
    assert to_activity_code("crypto exchange") == "VASP_CRYPTO"
    assert to_activity_code("Gambling, betting & casinos") == "GAMBLING"
    assert to_activity_code("VASP_CRYPTO") == "VASP_CRYPTO"
    assert to_activity_code("bakery") is None
    assert activity_from_nace("64.19") == "BANKING_REGULATED"
    assert activity_from_nace("6420") == "HOLDING_SHELL"
    assert activity_from_nace("92.00") == "GAMBLING"
    assert activity_label("VASP_CRYPTO").startswith("Virtual assets")


def test_create_customer_requires_and_normalises_country(app, client, tokens):
    h = auth(tokens["officer@test.io"])
    # Geography factors are installed from the official lists by the sync (as
    # seed-demo / ingest-watchlists do); the bare test fixture has none.
    with app.app_context():
        from api.engine import country_risk
        country_risk.sync(prefer_live=False)
    r = client.post("/api/customers", json={"name": "No Country Ltd", "customer_type": "COMPANY"}, headers=h)
    assert r.status_code == 400 and "country" in r.get_json()["message"]
    r = client.post("/api/customers", json={"name": "Bad Country Ltd", "country": "Narnia"}, headers=h)
    assert r.status_code == 400
    r = client.post("/api/customers", json={"name": "Named Country Ltd", "customer_type": "COMPANY",
                                            "country": "Islamic Republic of Iran",
                                            "business_activity": "crypto exchange platform"}, headers=h)
    assert r.status_code == 201, r.get_json()
    body = r.get_json()
    assert body["country"] == "IR" and body["country_name"] == "Iran"
    assert body["business_activity"] == "VASP_CRYPTO"
    assert body["business_activity_label"].startswith("Virtual assets")
    # FATF call-for-action (+35), EU high-risk list (+25) and the crypto
    # activity (+25) all fire on a customer typed with a NAME, not a code.
    assert body["risk_score"] >= 60 and body["risk_level"] in ("HIGH", "CRITICAL"), body


def test_unknown_activity_is_kept_as_detail_under_other(client, tokens):
    h = auth(tokens["officer@test.io"])
    r = client.post("/api/customers", json={"name": "Croissant SARL", "customer_type": "COMPANY",
                                            "country": "LU", "business_activity": "artisan bakery"}, headers=h)
    assert r.status_code == 201
    assert r.get_json()["business_activity"] == "OTHER"
    assert r.get_json()["business_activity_detail"] == "artisan bakery"


def test_patch_customer_recomputes_risk_and_audits(client, tokens):
    h = auth(tokens["officer@test.io"])
    r = client.post("/api/customers", json={"name": "Calm Trading SA", "customer_type": "COMPANY",
                                            "country": "LU", "business_activity": "software"}, headers=h)
    cid = r.get_json()["id"]; low = r.get_json()["risk_score"]
    r = client.patch(f"/api/customers/{cid}", json={"country": "North Korea", "business_activity": "casino"}, headers=h)
    assert r.status_code == 200, r.get_json()
    body = r.get_json()
    assert body["country"] == "KP" and body["business_activity"] == "GAMBLING"
    assert body["risk_score"] > low
    r = client.patch(f"/api/customers/{cid}", json={"country": "Atlantis"}, headers=h)
    assert r.status_code == 400


def test_country_factor_matches_any_country_on_the_file(app, client, tokens):
    """A resident of a listed jurisdiction is caught even when customer.country
    says otherwise — the official list looks at residence and nationality too."""
    h = auth(tokens["officer@test.io"])
    r = client.post("/api/customers", json={"name": "Expat Person", "customer_type": "INDIVIDUAL",
                                            "country": "LU"}, headers=h)
    cid = r.get_json()["id"]
    r = client.post(f"/api/customers/{cid}/kyc-form", json={"fields": {"residential_country": "Myanmar"}}, headers=h)
    assert r.status_code in (200, 201), r.get_json()
    with app.app_context():
        customer = db.session.get(Customer, cid)
        meth = RiskMethodology.query.filter_by(active=True).first()
        factor = RiskFactor(methodology_id=meth.id, code="GEO_TEST", label="test list", impact=35,
                            condition_type="COUNTRY_IN",
                            condition_value={"values": ["Myanmar"], "fields": ["country", "residence"]})
        db.session.add(factor); db.session.commit()
        factors, score, level, _v = risk_engine._evaluate(customer)
        fired = {f["code"]: f for f in factors}
        assert "GEO_TEST" in fired and fired["GEO_TEST"]["via"] == "residence=MM"


def test_catalogues_endpoint(client, tokens):
    r = client.get("/api/catalogues", headers=auth(tokens["officer@test.io"]))
    assert r.status_code == 200
    body = r.get_json()
    assert any(c["code"] == "LU" and c["name"] == "Luxembourg" for c in body["countries"])
    assert any(a["code"] == "VASP_CRYPTO" and a["high_risk"] for a in body["activities"])
