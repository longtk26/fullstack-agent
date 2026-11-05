import hashlib
import hmac
import time

HEADER = "X-Webhook-Signature"


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    """`t=<unix>,v1=<hex>`: HMAC-SHA256 over `<t>.<body>` (Story 10.8)."""
    timestamp = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def verify(secret: str, header: str | None, body: bytes, tolerance: int = 300, now: int | None = None) -> bool:
    """A signature made with `secret` over this exact body, no older (or newer) than `tolerance` seconds."""
    if not secret or not header:
        return False
    parts = dict(part.split("=", 1) for part in header.split(",") if "=" in part)
    try:
        timestamp = int(parts["t"])
    except (KeyError, ValueError):
        return False
    if abs((int(time.time()) if now is None else now) - timestamp) > tolerance:
        return False
    expected = sign(secret, body, timestamp).split(",v1=", 1)[1]
    return hmac.compare_digest(expected, parts.get("v1", ""))
