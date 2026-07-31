"""Editable risk methodology (the org's barème): a compliance team builds its
own scoring model — weighted factors + score bands — as a DRAFT, then activates
it. Editing is allowed only while DRAFT; activation freezes the version and
archives the previous one, so risk history stays interpretable."""
from conftest import auth


def _draft(client, tok, name="My barème"):
    return client.post("/api/risk/methodologies", headers=auth(tok),
                       json={"name": name}).get_json()


def test_create_edit_activate_flow(client, tokens):
    tok = tokens["officer@test.io"]
    m = _draft(client, tok)
    assert m["status"] == "DRAFT"
    assert m["active"] is False
    assert len(m["thresholds"]) == 4          # cloned/blank default bands
    mid = m["id"]

    # Add a factor.
    r = client.post(f"/api/risk/methodologies/{mid}/factors", headers=auth(tok),
                    json={"code": "pep", "label": "PEP detected", "impact": 30,
                          "condition_type": "FLAG",
                          "condition_value": {"field": "is_pep"}})
    assert r.status_code == 201
    fid = r.get_json()["id"]
    assert r.get_json()["code"] == "PEP"      # normalised upper-case

    # Edit it.
    r2 = client.patch(f"/api/risk/factors/{fid}", headers=auth(tok),
                      json={"impact": 45})
    assert r2.status_code == 200 and r2.get_json()["impact"] == 45

    # Set a valid, contiguous band set.
    r3 = client.put(f"/api/risk/methodologies/{mid}/thresholds", headers=auth(tok),
                    json={"thresholds": [
                        {"level": "LOW", "min_score": 0, "max_score": 24},
                        {"level": "MEDIUM", "min_score": 25, "max_score": 49},
                        {"level": "HIGH", "min_score": 50, "max_score": 79},
                        {"level": "CRITICAL", "min_score": 80, "max_score": None}]})
    assert r3.status_code == 200

    # Activate → becomes the org's live methodology.
    r4 = client.post(f"/api/risk/methodologies/{mid}/activate", headers=auth(tok))
    assert r4.status_code == 200
    assert r4.get_json()["status"] == "ACTIVE"
    assert r4.get_json()["active"] is True

    active = client.get("/api/risk/methodologies/active", headers=auth(tok)).get_json()
    assert active["id"] == mid                # the engine now uses the org barème


def test_active_methodology_is_frozen(client, tokens):
    tok = tokens["officer@test.io"]
    mid = _draft(client, tok)["id"]
    client.post(f"/api/risk/methodologies/{mid}/factors", headers=auth(tok),
                json={"code": "SANC", "label": "Sanctions", "impact": 40,
                      "condition_type": "FLAG",
                      "condition_value": {"field": "has_sanctions_match"}})
    client.post(f"/api/risk/methodologies/{mid}/activate", headers=auth(tok))

    # An active methodology can no longer be edited — you must clone a new draft.
    r = client.post(f"/api/risk/methodologies/{mid}/factors", headers=auth(tok),
                    json={"code": "X", "label": "x", "impact": 1,
                          "condition_type": "FLAG",
                          "condition_value": {"field": "is_pep"}})
    assert r.status_code == 400
    assert "draft" in r.get_json()["message"].lower()


def test_threshold_gap_is_rejected(client, tokens):
    tok = tokens["officer@test.io"]
    mid = _draft(client, tok)["id"]
    r = client.put(f"/api/risk/methodologies/{mid}/thresholds", headers=auth(tok),
                   json={"thresholds": [
                       {"level": "LOW", "min_score": 0, "max_score": 24},
                       {"level": "MEDIUM", "min_score": 30, "max_score": 49},   # gap 25-29
                       {"level": "HIGH", "min_score": 50, "max_score": 79},
                       {"level": "CRITICAL", "min_score": 80, "max_score": None}]})
    assert r.status_code == 400
    assert "gap or overlap" in r.get_json()["message"].lower()


def test_activation_requires_an_active_factor(client, tokens):
    tok = tokens["officer@test.io"]
    mid = _draft(client, tok)["id"]           # blank/cloned but we add none
    # If the clone brought factors, disable them so there is truly none active.
    m = next(x for x in client.get("/api/risk/methodologies", headers=auth(tok)).get_json()
             if x["id"] == mid)
    for f in m["factors"]:
        client.delete(f"/api/risk/factors/{f['id']}", headers=auth(tok))
    r = client.post(f"/api/risk/methodologies/{mid}/activate", headers=auth(tok))
    assert r.status_code == 400
    assert "factor" in r.get_json()["message"].lower()


def test_manage_permission_is_required(client, tokens):
    # Analyst lacks risk.manage; the technical admin deliberately lacks it too
    # (defining the barème is a compliance decision, not a technical one).
    for who in ("analyst@test.io", "admin@test.io"):
        r = client.post("/api/risk/methodologies", headers=auth(tokens[who]),
                        json={"name": "nope"})
        assert r.status_code == 403, who
