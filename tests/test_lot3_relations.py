"""Lot 3 — relations: persons carry the identity attributes screening needs,
intermediate holdings are first-class (and scoped), and linking an actor to
another file makes the group appear."""
from conftest import auth
from api.models import Address, db


def _customer(client, tok, name, ctype="COMPANY", **over):
    body = {"name": name, "customer_type": ctype, "country": "LU",
            "business_activity": "consulting", "allow_duplicate": True}
    body.update(over)
    r = client.post("/api/customers", headers=auth(tok), json=body)
    assert r.status_code == 201, r.get_json()
    return r.get_json()["id"]


def test_person_owner_carries_identity_attributes_and_address(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _customer(client, tok, "Identity Co")
    r = client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Anna Berg", "owner_kind": "PERSON", "relationship_type": "SHAREHOLDER",
        "percentage": 40, "date_of_birth": "1979-04-12", "nationalities": ["Belgium", "FR", "be"],
        "country": "Luxembourg", "gender": "f",
        "address": {"line1": "12 rue de la Gare", "city": "Luxembourg", "postal_code": "L-1616", "country": "LU"},
    })
    assert r.status_code == 201, r.get_json()
    owner = r.get_json()["owner"]
    assert owner["nationalities"] == ["BE", "FR"] and owner["nationality"] == "BE"
    assert owner["nationalities_names"] == ["Belgium", "France"]
    assert owner["gender"] == "F" and owner["date_of_birth"].startswith("1979-04-12")
    assert owner["country_of_residence"] == "LU"
    with client.application.app_context():
        addr = Address.query.filter_by(party_id=owner["id"]).one()
        assert addr.address_type == "RESIDENTIAL" and addr.country == "LU" and addr.city == "Luxembourg"
    bad = client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Bad Date", "owner_kind": "PERSON", "date_of_birth": "12/04/1979"})
    assert bad.status_code == 400


def test_intermediate_holding_is_first_class_and_scoped(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _customer(client, tok, "Layered SA")
    other = _customer(client, tok, "Unrelated SA")
    # a party that belongs to ANOTHER file's structure (the root itself is
    # created lazily, so give the other file a real owner first)
    foreign = client.post(f"/api/customers/{other}/ownership", headers=auth(tok), json={
        "owner_name": "Foreign Holding", "owner_kind": "ORGANIZATION", "percentage": 100}).get_json()["owner"]["id"]
    holding = client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Layered Holding BV", "owner_kind": "ORGANIZATION", "percentage": 60, "country": "NL"})
    assert holding.status_code == 201
    hid = holding.get_json()["owner"]["id"]
    # a person above the holding: effective ownership is the product along the chain
    person = client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Piet de Vries", "owner_kind": "PERSON", "percentage": 50, "owned_party_id": hid})
    assert person.status_code == 201, person.get_json()
    g = client.get(f"/api/customers/{cid}/ownership", headers=auth(tok)).get_json()
    piet = next(u for u in g["ubos"] if u["party"]["name"] == "Piet de Vries")
    assert piet["effective_ownership"] == 30 and piet["is_ubo"] is True
    assert {e["relationship_type"] for e in g["graph"]["edges"]} == {"SHAREHOLDER"}
    assert any(e["owned_party_id"] == hid for e in g["graph"]["edges"])
    # the target must belong to THIS structure: another file's root is refused
    hijack = client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Intruder", "owner_kind": "PERSON", "percentage": 10, "owned_party_id": foreign})
    assert hijack.status_code == 400
    assert "structure" in hijack.get_json()["message"]


def test_linking_a_shared_actor_connects_the_two_files(client, tokens):
    tok = tokens["officer@test.io"]
    a = _customer(client, tok, "Group Alpha SA")
    b = _customer(client, tok, "Group Beta SA")
    parent = client.post(f"/api/customers/{a}/ownership", headers=auth(tok), json={
        "owner_name": "Common Parent Holding", "owner_kind": "ORGANIZATION", "percentage": 100})
    pid = parent.get_json()["owner"]["id"]
    linked = client.post(f"/api/customers/{b}/ownership", headers=auth(tok), json={
        "link_party_id": pid, "owner_kind": "ORGANIZATION", "percentage": 100})
    assert linked.status_code == 201 and linked.get_json()["linked"] is True
    rel = client.get(f"/api/customers/{a}/relations", headers=auth(tok)).get_json()
    names = {c["name"] for c in rel["connections"]}
    assert "Group Beta SA" in names
