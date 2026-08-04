"""Per-related-party documents: a passport / proof of address is required for
EACH beneficial owner individually, not once for the company. The requirement
engine expands a per-party definition into one instance per UBO, tracked and
satisfied per person."""
import io

from conftest import auth


def _ph_company(client, tok, name="Meridian Privé SA"):
    return client.post("/api/customers", headers=auth(tok),
                       json={"name": name, "customer_type": "COMPANY",
                             "country": "Luxembourg",
                             "legal_form": "PRIVATELY_HELD"}).get_json()["id"]


def _ubo(client, tok, cid, name, pct=30):
    return client.post(f"/api/customers/{cid}/ownership", headers=auth(tok),
                       json={"owner_name": name, "owner_kind": "PERSON",
                             "relationship_type": "UBO", "percentage": pct}
                       ).get_json()["owner"]["id"]


def _evaluate(app, cid):
    with app.app_context():
        from api.engine import requirement_engine
        from api.models import Customer
        return {(ri.code, ri.party_id): ri.status
                for ri in requirement_engine.evaluate(Customer.query.get(cid))}


def test_per_party_expands_to_one_instance_per_ubo(client, tokens, app):
    tok = tokens["officer@test.io"]
    cid = _ph_company(client, tok)
    anna = _ubo(client, tok, cid, "Anna Berg", 40)
    boris = _ubo(client, tok, cid, "Boris Cole", 30)

    insts = _evaluate(app, cid)
    # A passport requirement exists for EACH UBO, keyed by party.
    assert insts.get(("UBO_IDENTITY_DOCS", anna)) == "MISSING"
    assert insts.get(("UBO_IDENTITY_DOCS", boris)) == "MISSING"
    assert insts.get(("UBO_PROOF_OF_ADDRESS", anna)) == "MISSING"
    assert insts.get(("UBO_PROOF_OF_ADDRESS", boris)) == "MISSING"


def test_document_satisfies_only_its_own_party(client, tokens, app):
    tok = tokens["officer@test.io"]
    cid = _ph_company(client, tok)
    anna = _ubo(client, tok, cid, "Anna Berg", 40)
    boris = _ubo(client, tok, cid, "Boris Cole", 30)

    # Anna's passport arrives (tagged to her party); Boris's does not.
    with app.app_context():
        from api.models import db, Document
        db.session.add(Document(customer_id=cid, party_id=anna,
                                doc_type="UBO_IDENTITY_DOCS",
                                file_url="stored://anna-passport", status="RECEIVED"))
        db.session.commit()

    insts = _evaluate(app, cid)
    assert insts[("UBO_IDENTITY_DOCS", anna)] == "RECEIVED"
    assert insts[("UBO_IDENTITY_DOCS", boris)] == "MISSING"   # not satisfied by Anna's


def test_no_per_party_rows_before_a_ubo_exists(client, tokens, app):
    tok = tokens["officer@test.io"]
    cid = _ph_company(client, tok, "Ownerless Holding SA")
    insts = _evaluate(app, cid)
    assert not any(code in ("UBO_IDENTITY_DOCS", "UBO_PROOF_OF_ADDRESS")
                   for code, _ in insts)


def test_upload_route_tags_the_document_to_a_party(client, tokens, app):
    tok = tokens["officer@test.io"]
    cid = _ph_company(client, tok)
    anna = _ubo(client, tok, cid, "Anna Berg", 40)

    r = client.post(f"/api/customers/{cid}/documents", headers=auth(tok),
                    data={"doc_type": "UBO_IDENTITY_DOCS", "party_id": str(anna),
                          "file": (io.BytesIO(b"%PDF-1.4 test"), "anna.pdf")},
                    content_type="multipart/form-data")
    assert r.status_code == 201
    assert r.get_json()["party_id"] == anna

    insts = _evaluate(app, cid)
    assert insts[("UBO_IDENTITY_DOCS", anna)] in ("RECEIVED", "VERIFIED")
