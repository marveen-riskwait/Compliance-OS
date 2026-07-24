"""Sumsub documentary IDV (paid, dormant until keyed): the terrain is wired —
starting IDV reports a clear 'configure app_token + secret_key' error with no
credentials, and the webhook signature check + normalisation work in isolation."""
from conftest import auth


def _customer(client, token, name):
    return client.post("/api/customers", headers=auth(token),
                       json={"name": name, "customer_type": "INDIVIDUAL",
                             "country": "Luxembourg"}).get_json()["id"]


def test_start_idv_without_credentials_is_clear(client, tokens):
    officer = tokens["officer@test.io"]
    cid = _customer(client, officer, "IDV NoKey Co")
    r = client.post(f"/api/customers/{cid}/idv/start", headers=auth(officer))
    assert r.status_code == 409
    msg = r.get_json()["message"].lower()
    assert "app_token" in msg and "secret_key" in msg


def test_webhook_signature_and_normalisation():
    import hashlib
    import hmac
    from api.integrations.providers.registry import ADAPTERS
    adapter = ADAPTERS["sumsub"](config={}, credentials={"secret_key": "s3cr3t"})

    body = b'{"applicantId":"abc","type":"IDENTITY","reviewResult":{"reviewAnswer":"GREEN"}}'
    good = hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert adapter.verify_webhook_signature(body, good) is True
    assert adapter.verify_webhook_signature(body, "deadbeef") is False

    import json
    result = adapter.normalize_webhook(json.loads(body))
    assert result.status == "PASSED"
    assert result.provider_reference == "abc"


def test_health_reports_degraded_without_keys():
    from api.integrations.providers.registry import ADAPTERS
    status, _ = ADAPTERS["sumsub"](config={}, credentials={}).health_check()
    assert status == "DEGRADED"
