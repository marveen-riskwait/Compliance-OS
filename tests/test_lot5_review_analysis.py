"""Lot 5 — review & analysis: no approval on an empty file without saying
why, reviews can be brought forward with a reason, every risk factor is
explainable, and the file carries the analyst's notes."""
from conftest import auth


def _company(client, tok, name="Gate Test SA"):
    r = client.post("/api/customers", headers=auth(tok), json={
        "name": name, "customer_type": "COMPANY", "country": "LU",
        "business_activity": "consulting", "allow_duplicate": True})
    assert r.status_code == 201
    return r.get_json()["id"]


def _initial_review(client, tok, cid):
    row = next(c for c in client.get("/api/customers", headers=auth(tok)).get_json() if c["id"] == cid)
    return row["onboarding"]["review_id"]


def test_approval_gate_blocks_then_overrides_with_reason(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    rid = _initial_review(client, tok, cid)
    assert client.post(f"/api/reviews/{rid}/start", headers=auth(tok)).status_code == 200
    r = client.post(f"/api/reviews/{rid}/complete", headers=auth(tok),
                    json={"decision": "APPROVED", "reason": "Looks fine to me"})
    assert r.status_code == 409, r.get_json()
    codes = {b["code"] for b in r.get_json()["blockers"]}
    assert "MISSING_REQUIREMENTS" in codes and "SCREENING_NOT_RUN" in codes
    # a rejection is never gated
    # an override needs a real reason
    short = client.post(f"/api/reviews/{rid}/complete", headers=auth(tok),
                        json={"decision": "APPROVED", "reason": "Looks fine", "override_reason": "ok"})
    assert short.status_code == 409
    ok = client.post(f"/api/reviews/{rid}/complete", headers=auth(tok),
                     json={"decision": "APPROVED", "reason": "Looks fine",
                           "override_reason": "Low-risk pilot client, documents arriving next week"})
    assert ok.status_code == 200, ok.get_json()
    audit = client.get("/api/audit?entity_type=review", headers=auth(tok)).get_json()
    entries = audit if isinstance(audit, list) else audit.get("entries") or audit.get("items") or []
    assert any(e.get("action") == "REVIEW_GATE_OVERRIDDEN" for e in entries)


def test_trigger_review_requires_a_reason_and_is_audited(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    bad = client.post(f"/api/customers/{cid}/reviews", headers=auth(tok), json={"review_type": "EVENT_DRIVEN_REVIEW"})
    assert bad.status_code == 400
    r = client.post(f"/api/customers/{cid}/reviews", headers=auth(tok),
                    json={"review_type": "EVENT_DRIVEN_REVIEW", "reason": "Change of ownership reported by the RM"})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["trigger"].startswith("Manual: Change of ownership")
    assert r.get_json()["status"] == "DUE"


def test_risk_breakdown_lists_every_factor(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    client.post(f"/api/customers/{cid}/ownership", headers=auth(tok), json={
        "owner_name": "Deep Holding", "owner_kind": "ORGANIZATION", "percentage": 100})
    b = client.get(f"/api/customers/{cid}/risk-breakdown", headers=auth(tok)).get_json()
    assert b["factors"], "no factors"
    assert {"code", "label", "impact", "fired", "condition", "driven_by"} <= set(b["factors"][0])
    assert any(not f["fired"] for f in b["factors"]) or len(b["factors"]) == 1
    assert b["methodology"]["version"] and isinstance(b["history"], list)
    assert b["stored_score"] == client.get(f"/api/customers/{cid}", headers=auth(tok)).get_json()["customer"]["risk_score"]


def test_notes_summary_and_comments_and_export(client, tokens):
    tok = tokens["officer@test.io"]
    cid = _company(client, tok)
    r = client.post(f"/api/customers/{cid}/notes", headers=auth(tok),
                    json={"kind": "ANALYSIS_SUMMARY", "text": "Low-risk consultancy, UBO verified via register."})
    assert r.status_code == 201 and r.get_json()["summary"]["text"].startswith("Low-risk")
    r = client.post(f"/api/customers/{cid}/notes", headers=auth(tok),
                    json={"kind": "ANALYSIS_SUMMARY", "text": "Updated: now MEDIUM after adverse media."})
    assert r.get_json()["summary"]["text"].startswith("Updated") and r.get_json()["comments"] == []
    r = client.post(f"/api/customers/{cid}/notes", headers=auth(tok), json={"text": "Called the RM, documents promised."})
    assert r.status_code == 201 and len(r.get_json()["comments"]) == 1
    nid = r.get_json()["comments"][0]["id"]
    assert r.get_json()["comments"][0]["author_name"]
    bad = client.post(f"/api/customers/{cid}/notes", headers=auth(tok), json={"kind": "WHATEVER", "text": "x"})
    assert bad.status_code == 400
    exp = client.get(f"/api/customers/{cid}/data-export", headers=auth(tok)).get_json()
    assert any(n["text"].startswith("Called the RM") for n in exp["notes"])
    assert client.delete(f"/api/customers/{cid}/notes/{nid}", headers=auth(tok)).status_code == 200
    assert client.get(f"/api/customers/{cid}/notes", headers=auth(tok)).get_json()["comments"] == []
