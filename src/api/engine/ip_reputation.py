"""IP reputation at the point of connection (AbuseIPDB).

This is a security control on the authentication layer, not a compliance form:
the source IP of whoever signs in is checked automatically. A flagged IP (high
abuse score or a Tor exit node) triggers a step-up second factor at login, and
— for a portal customer signing in to onboard — an AML fraud signal on their file.

Every function here is best-effort and MUST NOT break sign-in: no key, a slow or
unreachable AbuseIPDB, a private/loopback address — all resolve to "no signal"
and login proceeds. A step-up is only ever forced on a positive, confident hit.
"""
import ipaddress
import os

# Tight timeout on the login path so a slow AbuseIPDB never hangs sign-in.
_LOGIN_TIMEOUT = float(os.getenv("IP_ABUSE_LOGIN_TIMEOUT", "4"))


def _threshold():
    try:
        return int(os.getenv("IP_ABUSE_THRESHOLD", "50"))
    except ValueError:
        return 50


def client_ip():
    """The real client IP behind the Fly proxy: Fly-Client-IP, else the
    left-most X-Forwarded-For hop, else the socket peer."""
    from flask import request
    fly = request.headers.get("Fly-Client-IP")
    if fly:
        return fly.strip()
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr


def is_public_ip(ip):
    """Only public, routable addresses are worth checking — dev/localhost and
    internal traffic are skipped."""
    try:
        addr = ipaddress.ip_address((ip or "").strip())
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local
                or addr.is_reserved or addr.is_multicast)


def check(organization_id, ip):
    """Return a normalised AbuseIPDB result for an IP, or None when there is no
    signal to act on (no key, private IP, provider off, or any error). Never raises."""
    if not is_public_ip(ip):
        return None
    try:
        from api.engine.provider_service import find_provider
        from api.integrations.providers.registry import get_adapter
        provider = find_provider(organization_id, name="AbuseIPDB",
                                 provider_type="FRAUD")
        if provider is None:
            return None
        adapter = get_adapter(provider)
        return adapter.check(ip, timeout=_LOGIN_TIMEOUT)
    except Exception:
        # Fail open: a reputation lookup must never stand between a legitimate
        # user and their session.
        return None


def is_flagged(result):
    """A confident hit: abuse score at/over threshold, or a Tor exit node."""
    if not result:
        return False
    return int(result.get("abuse_score") or 0) >= _threshold() \
        or bool(result.get("is_tor"))
