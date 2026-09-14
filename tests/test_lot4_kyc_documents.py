"""Lot 4 — KYC & documents: the form and the file agree on the name, answers
can hide/show and name people, contacts are many, one file can serve several
requirements, and an expired document stops counting."""
from io import BytesIO
import json
from conftest import auth


def _company(client, tok, name="Docs & Forms SA"):
    r = client.post("/api/customers", headers=auth(tok), json={
        "name": name, "customer_type": "COMPANY", "country": "LU",
        "business_activity": "consulting", "allow_duplicate": True})
    assert r.status_code == 201
    return r.get_json()["id"]


def _upload(client, tok, cid, doc_type, **fields):
    data = {"file": (BytesIO(b"%PDF-1.4 test"), "scan.pdf"), "doc_type": doc_type, **fields}
    return client.post(f"/api/customers/{cid}/documents", headers=auth(tok), data=data,
                       content_type="multipart/form-data")


def test_legal_name_is_prefilled_and_renames_the_file(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok, "Old Name SA")
    form = client.get(f"/api/customers/{cid}/kyc-form", headers=auth(tok)).get_json()
    assert form["values"]["legal_name"]["value"] == "Old Name SA"
    assert form["values"]["legal_name"]["source"] == "prefill"
    r = client.post(f"/api/customers/{cid}/kyc-form", headers=auth(tok),
                    json={"fields": {"legal_name": "New Name SA"}})
    assert r.status_code == 200
    assert client.get(f"/api/customers/{cid}", headers=auth(tok)).get_json()["customer"]["name"] == "New Name SA"


def test_show_if_contacts_and_pep_persons(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    form = client.get(f"/api/customers/{cid}/kyc-form", headers=auth(tok)).get_json()
    fields = {f["key"]: f for s in form["sections"] for f in s["fields"]}
    assert fields["control_by_other_means_detail"]["show_if"] == {"key": "control_by_other_means", "equals": "Yes"}
    assert fields["pep_persons"]["type"] == "parties" and fields["contact_persons"]["type"] == "contacts"
    contacts = [{"name": "Ana Lopez", "title": "CFO", "email": "ana@x.lu", "phone": "+352 1"}, {"name": "", "title": "ghost"}]
    r = client.post(f"/api/customers/{cid}/kyc-form", headers=auth(tok),
                    json={"fields": {"contact_persons": json.dumps(contacts)}})
    assert r.status_code == 200
    saved = client.get(f"/api/customers/{cid}/kyc-form", headers=auth(tok)).get_json()["values"]["contact_persons"]["value"]
    assert json.loads(saved) == [{"name": "Ana Lopez", "title": "CFO", "email": "ana@x.lu", "phone": "+352 1"}]
    # a person of the file, ticked as the PEP, is flagged on their own record
    owner = client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Pierre Politique", "owner_kind": "PERSON", "percentage": 30}).get_json()["owner"]
    form = client.get(f"/api/customers/{cid}/kyc-form", headers=auth(tok)).get_json()
    assert any(p["id"] == owner["id"] for p in form["parties"])
    r = client.post(f"/api/customers/{cid}/kyc-form", headers=auth(tok),
                    json={"fields": {"pep_self_declaration": "Yes", "pep_persons": str(owner["id"])}})
    assert r.status_code == 200
    assert client.get(f"/api/parties/{owner['id']}", headers=auth(tok)).get_json()["is_pep"] is True
    prov = client.get(f"/api/customers/{cid}/fields", headers=auth(tok)).get_json()
    pep = next(f for f in prov if f["field_key"] == "pep_self_declaration")
    assert pep["label"].startswith("Is the customer") and pep["source_label"].startswith("Declared in the KYC form")


def test_reuse_and_expiry(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    up = _upload(client, tok, cid, "CERTIFICATE_OF_INCORPORATION", expiry_date="2020-01-31")
    assert up.status_code == 201, up.get_json()
    doc = up.get_json()
    assert doc["expiry_date"].startswith("2020-01-31") and doc["expired"] is True
    # the same file also serves as the register extract — no second upload
    reused = client.post(f"/api/customers/{cid}/documents/{doc['id']}/reuse", headers=auth(tok),
                         json={"doc_type": "REGISTER_EXTRACT"})
    assert reused.status_code == 201, reused.get_json()
    assert reused.get_json()["file_url"] == doc["file_url"] and reused.get_json()["doc_type"] == "REGISTER_EXTRACT"
    same = client.post(f"/api/customers/{cid}/documents/{doc['id']}/reuse", headers=auth(tok),
                       json={"doc_type": "CERTIFICATE_OF_INCORPORATION"})
    assert same.status_code == 400
    # the sweep marks the past-dated documents EXPIRED and they stop counting
    run = client.post("/api/monitoring/run", headers=auth(tok))
    assert run.status_code == 200 and run.get_json()["documents"]["expired"] >= 2
    docs = client.get(f"/api/customers/{cid}/kyc-form", headers=auth(tok)).get_json()["documents"]
    assert all(d["status"] == "EXPIRED" for d in docs if d["doc_type"] in ("CERTIFICATE_OF_INCORPORATION", "REGISTER_EXTRACT"))
    # …and the requirement the expired file used to satisfy is open again
    from api.models import RequirementInstance, RequirementDefinition
    with client.application.app_context():
        for inst in RequirementInstance.query.filter_by(customer_id=cid, kind="DOCUMENT").all():
            d = RequirementDefinition.query.get(inst.definition_id)
            if d is not None and d.doc_type in ("CERTIFICATE_OF_INCORPORATION", "REGISTER_EXTRACT"):
                assert inst.status == "MISSING", (d.doc_type, inst.status)
    bad = _upload(client, tok, cid, "PASSPORT", expiry_date="31/01/2030")
    assert bad.status_code == 400


def test_address_label_and_address_country_feeds_geography(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    r = client.post(f"/api/customers/{cid}/addresses", headers=auth(tok), json={
        "label": "Registered office", "line1": "1 Kim Il-sung Square", "city": "Pyongyang",
        "country": "KP", "address_type": "REGISTERED"})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["label"] == "Registered office"
    from api.engine.risk_engine import _country_values
    from api.models import Customer
    with client.application.app_context():
        have = _country_values(Customer.query.get(cid))
        assert have.get("registered_address") == "KP"
