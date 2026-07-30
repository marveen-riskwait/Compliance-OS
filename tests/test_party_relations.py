"""Phase A of the entity relations feature: shared actors (identity resolution).
The same person/entity added to a second file is proposed as a candidate and,
once linked, reuses the SAME party record — no duplicate, and the ownership
graph now connects both companies through the shared actor."""
from conftest import auth


def _company(client, tok, name, country="Luxembourg"):
    return client.post("/api/customers", headers=auth(tok),
                       json={"name": name, "customer_type": "COMPANY",
                             "country": country}).get_json()["id"]


def test_link_existing_actor_reuses_party(client, tokens, app):
    tok = tokens["officer@test.io"]
    a = _company(client, tok, "Alpha Crypto Ltd", "Panama")
    r = client.post(f"/api/customers/{a}/ownership", headers=auth(tok),
                    json={"owner_name": "John Smith", "owner_kind": "PERSON",
                          "relationship_type": "UBO", "percentage": 48,
                          "nationality": "United Kingdom"})
    assert r.status_code == 201
    john_id = r.get_json()["owner"]["id"]

    b = _company(client, tok, "Gamma Trading Ltd")
    # Candidate lookup on the second file finds the known John Smith.
    cands = client.get(f"/api/customers/{b}/party-candidates?name=John%20Smith&kind=PERSON",
                       headers=auth(tok)).get_json()
    cand = next((x for x in cands if x["id"] == john_id), None)
    assert cand is not None and cand["match_score"] >= 90
    assert any(l["name"] == "Alpha Crypto Ltd" for l in cand["appears_in"])

    # Link (reuse) instead of creating a new party.
    r2 = client.post(f"/api/customers/{b}/ownership", headers=auth(tok),
                     json={"link_party_id": john_id, "relationship_type": "UBO",
                           "percentage": 30})
    assert r2.status_code == 201
    body = r2.get_json()
    assert body["linked"] is True
    assert body["owner"]["id"] == john_id          # same actor reused

    with app.app_context():
        from api.models import Party, OwnershipRelationship
        # No duplicate John Smith — the actor is a single shared record.
        assert Party.query.filter_by(kind="PERSON", name="John Smith").count() == 1
        owned = {e.owned_party_id for e in OwnershipRelationship.query
                 .filter_by(owner_party_id=john_id, active=True)}
        assert len(owned) == 2                       # John links BOTH companies


def test_person_does_not_match_a_company(client, tokens):
    tok = tokens["officer@test.io"]
    a = _company(client, tok, "Holdco One")
    client.post(f"/api/customers/{a}/ownership", headers=auth(tok),
                json={"owner_name": "Acme Registry Ltd", "owner_kind": "ORGANIZATION",
                      "relationship_type": "SHAREHOLDER", "percentage": 60})
    cands = client.get(f"/api/customers/{a}/party-candidates?name=Acme%20Registry&kind=PERSON",
                       headers=auth(tok)).get_json()
    assert all(x["kind"] != "ORGANIZATION" for x in cands)


def test_no_candidate_for_unknown_name(client, tokens):
    tok = tokens["officer@test.io"]
    a = _company(client, tok, "Solo Co")
    cands = client.get(f"/api/customers/{a}/party-candidates?name=Zephyr%20Nobody&kind=PERSON",
                       headers=auth(tok)).get_json()
    assert cands == []
