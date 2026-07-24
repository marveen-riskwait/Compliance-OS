"""Source-IP reputation at login (AbuseIPDB).

A flagged sign-in IP forces a step-up emailed code even on an account with no
enrolled MFA, and — for a portal customer — raises an AML fraud signal on their
file. The check is best-effort: private IPs and errors resolve to no signal and
login proceeds untouched.
"""
from conftest import auth


def _login(client, email, password="pw"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def _flag(monkeypatch, result):
    from api.engine import ip_reputation
    monkeypatch.setattr(ip_reputation, "check", lambda org, ip: result)


FLAGGED = {"ip": "185.220.101.1", "abuse_score": 100, "total_reports": 172,
           "country": "DE", "is_tor": True, "usage_type": "hosting", "isp": "x"}
CLEAN = {"ip": "8.8.8.8", "abuse_score": 0, "total_reports": 0, "country": "US",
         "is_tor": False, "usage_type": "cdn", "isp": "Google"}


def test_flagged_ip_forces_step_up_and_code_completes_login(client, tokens, monkeypatch):
    sent = {}
    from api.integrations import mailer
    monkeypatch.setattr(mailer, "send",
                        lambda to, subject, body, **k: sent.update(body=body) or {"sent": True})
    _flag(monkeypatch, FLAGGED)

    # officer has no MFA enrolled — normally a one-step login.
    r = _login(client, "officer@test.io").get_json()
    assert r["mfa_required"] is True
    assert r["step_up"] is True and r["method"] == "EMAIL_OTP"
    assert "flagged ip" in r["reason"].lower()

    code = sent["body"].split("code is: ")[1].split()[0].strip()
    ok = client.post("/api/auth/mfa", headers=auth(r["ticket"]), json={"code": code})
    assert ok.status_code == 200 and "token" in ok.get_json()


def test_step_up_rejects_a_wrong_code(client, tokens, monkeypatch):
    from api.integrations import mailer
    monkeypatch.setattr(mailer, "send", lambda *a, **k: {"sent": True})
    _flag(monkeypatch, FLAGGED)
    r = _login(client, "officer@test.io").get_json()
    bad = client.post("/api/auth/mfa", headers=auth(r["ticket"]), json={"code": "000000"})
    assert bad.status_code == 401


def test_clean_ip_logs_in_one_step(client, tokens, monkeypatch):
    _flag(monkeypatch, CLEAN)
    r = _login(client, "analyst@test.io")
    assert r.status_code == 200
    assert "token" in r.get_json() and "mfa_required" not in r.get_json()


def test_portal_login_from_flagged_ip_raises_fraud_signal(client, tokens, app, monkeypatch):
    from api.integrations import mailer
    monkeypatch.setattr(mailer, "send", lambda *a, **k: {"sent": True})
    _flag(monkeypatch, FLAGGED)

    from api.models import db, User, Customer, ComplianceAlert
    from api.auth import hash_password
    from api.rbac import get_role
    with app.app_context():
        c = Customer.query.filter_by(name="Marie Dupont").first()
        role = get_role("CUSTOMER_USER")
        db.session.add(User(email="portal-flagged@test.io", full_name="Client",
                            role="CUSTOMER_USER", role_id=role.id if role else None,
                            password=hash_password("pw"), organization_id=c.organization_id,
                            customer_id=c.id, is_active=True))
        db.session.commit()
        cid = c.id

    r = _login(client, "portal-flagged@test.io").get_json()
    assert r["step_up"] is True

    with app.app_context():
        assert ComplianceAlert.query.filter_by(
            customer_id=cid, alert_type="IP_FRAUD_SIGNAL").count() >= 1


def test_check_is_best_effort_and_never_raises():
    from api.engine import ip_reputation
    assert ip_reputation.is_public_ip("10.0.0.1") is False       # private
    assert ip_reputation.is_public_ip("127.0.0.1") is False      # loopback
    assert ip_reputation.is_public_ip("8.8.8.8") is True
    assert ip_reputation.is_flagged(None) is False
    assert ip_reputation.is_flagged({"abuse_score": 10, "is_tor": False}) is False
    assert ip_reputation.is_flagged({"abuse_score": 0, "is_tor": True}) is True
