"""Adapters prepared for real vendors (Sumsub, Trulioo, ComplyAdvantage).

These are wired for the normalization + webhook pipeline but do NOT call the
vendors until credentials are configured — they never invent data. `health_check`
reports DEGRADED when the API key is missing; live calls raise a clear error so a
failed integration is never silently ignored. Webhook normalization maps each
vendor's payload shape into the internal NormalizedResult.
"""
import hashlib
import hmac
import json
import ssl
import time
import urllib.error
import urllib.request

from api.integrations.providers.base import (
    KYCProvider, AMLScreeningProvider, NormalizedResult,
)


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class _CredentialedProvider:
    required_credential = "api_key"

    def _require_key(self):
        if not self.credentials.get(self.required_credential):
            raise RuntimeError(
                f"{self.adapter_key}: missing credential '{self.required_credential}'. "
                "Configure it in Administration → Integrations before use.")

    def health_check(self):
        if not self.credentials.get(self.required_credential):
            return ("DEGRADED", "API key not configured")
        return ("UP", "credentials present (live check not run)")


class SumsubKYCProvider(_CredentialedProvider, KYCProvider):
    """Sumsub documentary identity verification (passport/ID + selfie/liveness).

    Terrain prepared but dormant: Sumsub is a paid vendor. Configure two
    credentials in Administration → Integrations — `app_token` and
    `secret_key` — plus a `level_name` config (the Sumsub verification level),
    and enable the provider. Every call is a REAL, HMAC-signed request to
    api.sumsub.com; nothing is invented, and it stays disabled until keyed.

    The onboarding flow, when live:
      1. create_verification(subject) creates a Sumsub applicant and returns a
         short-lived WebSDK access token;
      2. the customer completes the flow in the Sumsub WebSDK (front-end);
      3. Sumsub posts a webhook to /api/webhooks/providers/sumsub, verified by
         verify_webhook_signature and normalised by normalize_webhook.
    """
    adapter_key = "sumsub"
    _BASE = "https://api.sumsub.com"

    def _require_key(self):
        missing = [k for k in ("app_token", "secret_key")
                   if not (self.credentials.get(k) or "").strip()]
        if missing:
            raise RuntimeError(
                f"sumsub: missing credential(s) {', '.join(missing)}. Configure "
                "app_token and secret_key in Administration → Integrations "
                "(Sumsub is a paid vendor) before use.")

    def health_check(self):
        if any(not (self.credentials.get(k) or "").strip()
               for k in ("app_token", "secret_key")):
            return ("DEGRADED", "app_token / secret_key not configured")
        return ("UP", "credentials present (live check not run)")

    def _signed(self, method, path, body=b""):
        """A Sumsub request signed with the app-secret HMAC (X-App-Access-Sig)."""
        app_token = (self.credentials.get("app_token") or "").strip()
        secret = (self.credentials.get("secret_key") or "").strip()
        ts = str(int(time.time()))
        raw = body if isinstance(body, bytes) else (body or "").encode()
        sig = hmac.new(secret.encode(), ts.encode() + method.encode()
                       + path.encode() + raw, hashlib.sha256).hexdigest()
        req = urllib.request.Request(self._BASE + path, data=raw or None,
                                     method=method, headers={
            "X-App-Token": app_token,
            "X-App-Access-Sig": sig,
            "X-App-Access-Ts": ts,
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=20,
                                        context=_ssl_context()) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise RuntimeError("sumsub: credentials rejected (401/403)")
            raise RuntimeError(f"sumsub: HTTP {exc.code}")

    def create_verification(self, subject):
        """Create an applicant and mint a WebSDK access token for the front-end."""
        self._require_key()
        level = (self.config.get("level_name") or "basic-kyc-level")
        ext_id = str(subject.get("customer_id") or subject.get("id") or "")
        # 1. Applicant (idempotent per externalUserId on Sumsub's side).
        applicant = self._signed(
            "POST", f"/resources/applicants?levelName={level}",
            json.dumps({"externalUserId": ext_id}))
        applicant_id = applicant.get("id")
        # 2. Short-lived token the WebSDK uses to run the flow in the browser.
        token = self._signed(
            "POST", f"/resources/accessTokens?userId={ext_id}&levelName={level}")
        return {"provider_reference": applicant_id,
                "access_token": token.get("token"),
                "level_name": level, "status": "PENDING"}

    def get_verification_status(self, provider_reference):
        self._require_key()
        data = self._signed("GET", f"/resources/applicants/{provider_reference}/status")
        answer = (data.get("reviewResult", {}).get("reviewAnswer") or "").upper()
        status = {"GREEN": "PASSED", "RED": "FAILED"}.get(answer, "PENDING")
        return {"status": status, "data": data}

    def verify_webhook_signature(self, raw_body, signature_header):
        """Sumsub signs webhooks with X-Payload-Digest (HMAC-SHA256, secret_key)."""
        secret = (self.credentials.get("secret_key") or "").strip()
        if not secret or not signature_header:
            return False
        digest = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest, signature_header)

    def normalize_webhook(self, payload):
        answer = (payload.get("reviewResult", {}).get("reviewAnswer") or "").upper()
        status = {"GREEN": "PASSED", "RED": "FAILED"}.get(answer, "PENDING")
        return NormalizedResult(
            provider="sumsub",
            provider_reference=payload.get("applicantId"),
            result_type=payload.get("type", "IDENTITY"),
            status=status, data=payload, raw=payload)


class TruliooKYCProvider(_CredentialedProvider, KYCProvider):
    adapter_key = "trulioo"

    def create_verification(self, subject):
        self._require_key()
        raise RuntimeError("Trulioo live verification not enabled in this build")

    def normalize_webhook(self, payload):
        record = (payload.get("Record") or {})
        status = "PASSED" if record.get("RecordStatus") == "match" else "FAILED"
        return NormalizedResult(
            provider="trulioo",
            provider_reference=payload.get("TransactionID"),
            result_type="IDENTITY", status=status, data=payload, raw=payload)


class ComplyAdvantageAMLProvider(_CredentialedProvider, AMLScreeningProvider):
    adapter_key = "comply_advantage"

    def screen_subject(self, subject):
        self._require_key()
        raise RuntimeError("ComplyAdvantage live screening not enabled in this build")

    def normalize_webhook(self, payload):
        match = payload.get("match_status") or payload.get("status")
        status = "MATCH" if match in ("potential_match", "true_positive") else "PASSED"
        return NormalizedResult(
            provider="comply_advantage",
            provider_reference=str(payload.get("search_id") or payload.get("id") or ""),
            result_type="SCREENING", status=status, data=payload, raw=payload)
