"""Group / network risk: a customer's risk aggregated across the economic group
it belongs to — the connected component of files linked through shared actors.
A group is only as clean as its riskiest member, and a shared PEP is a red flag
in itself; a clean file connected to a HIGH-risk relative inherits that signal."""
from conftest import auth


def _company(client, tok, name, country="Luxembourg"):
    return client.post("/api/customers", headers=auth(tok),
                       json={"name": name, "customer_type": "COMPANY",
                             "country": country}).get_json()["id"]


def _share_actor(client, tok, a, b, name, pct_a=60, pct_b=40, nationality="Sweden"):
    """Add `name` as a UBO of A, then reuse the SAME party as a UBO of B."""
    r = client.post(f"/api/customers/{a}/ownership", headers=auth(tok),
                    json={"owner_name": name, "owner_kind": "PERSON",
                          "relationship_type": "UBO", "percentage": pct_a,
                          "nationality": nationality})
    pid = r.get_json()["owner"]["id"]
    client.post(f"/api/customers/{b}/ownership", headers=auth(tok),
                json={"link_party_id": pid, "relationship_type": "UBO",
                      "percentage": pct_b})
    return pid


def test_group_risk_inherited_from_high_member(client, tokens, app):
    tok = tokens["officer@test.io"]
    a = _company(client, tok, "Nordic Parent SA")
    b = _company(client, tok, "Nordic Sub SA")
    ingrid = _share_actor(client, tok, a, b, "Ingrid Berg")

    # Make the SISTER file (B) HIGH risk; A stays clean on its own.
    with app.app_context():
        from api.models import db, Customer, RiskAssessment
        cb = Customer.query.filter_by(name="Nordic Sub SA").first()
        cb.risk_level, cb.risk_score = "HIGH", 78
        db.session.add(RiskAssessment(
            customer_id=cb.id, score=78, level="HIGH",
            factors=[{"code": "GEOGRAPHY",
                      "label": "High-risk jurisdiction", "impact": 20}],
            required_actions=[], reason="test"))
        db.session.commit()

    g = client.get(f"/api/customers/{a}/group-risk", headers=auth(tok)).get_json()

    assert g["group_size"] == 2
    assert {m["customer_id"] for m in g["members"]} == {a, b}
    assert g["peak_level"] == "HIGH"
    assert g["inherited"] is True                       # A is clean but the group is HIGH
    assert g["distribution"]["HIGH"] == 1

    # The shared actor bridges both files.
    bridge = next(br for br in g["bridges"] if br["party_id"] == ingrid)
    assert {c["customer_id"] for c in bridge["connects"]} >= {a, b}

    # The HIGH sister's factor surfaces as a group driver, attributed to it.
    assert any(d["source"] == "member" and d["customer_id"] == b
               and d["code"] == "GEOGRAPHY" for d in g["drivers"])


def test_group_risk_shared_pep_is_a_driver(client, tokens, app):
    tok = tokens["officer@test.io"]
    a = _company(client, tok, "Helios Holding SA")
    b = _company(client, tok, "Helios Trading SA")
    pid = _share_actor(client, tok, a, b, "Viktor Petrov")

    with app.app_context():
        from api.models import db, Party
        p = Party.query.get(pid)
        p.is_pep, p.pep_type = True, "FOREIGN"
        db.session.commit()

    g = client.get(f"/api/customers/{a}/group-risk", headers=auth(tok)).get_json()

    bridge = next(br for br in g["bridges"] if br["party_id"] == pid)
    assert bridge["is_pep"] is True
    assert any(d["source"] == "bridge" and d["code"] == "SHARED_PEP"
               for d in g["drivers"])


def test_group_risk_single_entity_has_no_group(client, tokens):
    tok = tokens["officer@test.io"]
    a = _company(client, tok, "Solitude SA")
    client.post(f"/api/customers/{a}/ownership", headers=auth(tok),
                json={"owner_name": "Private Owner", "owner_kind": "PERSON",
                      "relationship_type": "UBO", "percentage": 100})

    g = client.get(f"/api/customers/{a}/group-risk", headers=auth(tok)).get_json()

    assert g["group_size"] == 1
    assert g["bridges"] == []
    assert g["inherited"] is False
    assert g["peak_level"] == g["self_level"]
