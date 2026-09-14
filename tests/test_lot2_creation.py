"""Lot 2 — creation & duplicates: the book says where each file stands,
suggestions tell homonyms apart, and a duplicate is caught before it exists."""
from conftest import auth


def _create(client, tok, **over):
    body = {"name": "Duplicate Probe", "customer_type": "INDIVIDUAL", "country": "LU"}
    body.update(over)
    return client.post("/api/customers", headers=auth(tok), json=body)


def test_list_and_detail_carry_onboarding_state_and_validity(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _create(client, tok, name="Onboarding Probe").get_json()["id"]
    row = next(c for c in client.get("/api/customers", headers=auth(tok)).get_json() if c["id"] == cid)
    assert row["onboarding"]["state"] == "PENDING_REVIEW" and row["valid_until"] is None
    # approve the initial KYC review: the file becomes ACTIVE and is valid until
    # the next periodic review
    rid = row["onboarding"]["review_id"]
    assert client.post(f"/api/reviews/{rid}/start", headers=auth(tok)).status_code == 200
    r = client.post(f"/api/reviews/{rid}/complete", headers=auth(tok),
                    json={"decision": "APPROVED", "reason": "All checks done"})
    assert r.status_code == 200
    row = next(c for c in client.get("/api/customers", headers=auth(tok)).get_json() if c["id"] == cid)
    assert row["status"] == "ACTIVE"
    assert row["onboarding"]["state"] == "APPROVED" and row["valid_until"]
    assert row["validity_lapsed"] is False
    detail = client.get(f"/api/customers/{cid}", headers=auth(tok)).get_json()
    assert detail["customer"]["onboarding"]["state"] == "APPROVED"
    assert detail["customer"]["valid_until"] == row["valid_until"]


def test_suggestions_filter_by_type_and_carry_disambiguators(client, tokens):
    tok = tokens["officer@test.io"]
    _create(client, tok, name="Homonym Holdings", customer_type="COMPANY", business_activity="software")
    _create(client, tok, name="Homonym Holder", customer_type="INDIVIDUAL", date_of_birth="1980-02-03")
    both = client.get("/api/name-suggestions?q=homonym", headers=auth(tok)).get_json()["customers"]
    assert {c["name"] for c in both} >= {"Homonym Holdings", "Homonym Holder"}
    only_companies = client.get("/api/name-suggestions?q=homonym&customer_type=COMPANY",
                                headers=auth(tok)).get_json()["customers"]
    assert {c["customer_type"] for c in only_companies} == {"COMPANY"}
    person = next(c for c in both if c["name"] == "Homonym Holder")
    assert person["country_name"] == "Luxembourg"
    assert person["date_of_birth"] == "1980-02-03"
    assert person["onboarding"]["state"] == "PENDING_REVIEW"


def test_duplicate_is_refused_unless_homonym_or_confirmed(client, tokens):
    tok = tokens["officer@test.io"]
    first = _create(client, tok, name="Jean Dupont", date_of_birth="1970-01-01")
    assert first.status_code == 201
    # same name, same type, no distinguishing date of birth -> 409 with the file to open
    dup = _create(client, tok, name="  jean   DUPONT ")
    assert dup.status_code == 409, dup.get_json()
    body = dup.get_json()
    assert body["existing"][0]["id"] == first.get_json()["id"]
    assert body["existing"][0]["onboarding"]["state"] == "PENDING_REVIEW"
    # a different date of birth is a homonym, not a duplicate
    homonym = _create(client, tok, name="Jean Dupont", date_of_birth="1985-05-05")
    assert homonym.status_code == 201
    # a company with the same name is a different kind of file
    company = _create(client, tok, name="Jean Dupont", customer_type="COMPANY", business_activity="consulting")
    assert company.status_code == 201
    # and an explicit confirmation always goes through
    forced = _create(client, tok, name="Jean Dupont", allow_duplicate=True)
    assert forced.status_code == 201
    bad = _create(client, tok, name="Bad Date", date_of_birth="01/02/1990")
    assert bad.status_code == 400
