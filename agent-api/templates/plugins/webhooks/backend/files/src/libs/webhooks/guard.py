import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeTarget(ValueError):
    """A webhook URL this app will not call: not http(s), or an address inside a private network."""


def check_target(url: str, allow_private: bool = False) -> None:
    """SSRF guard (Story 10.8): refuses private, loopback, link-local and reserved addresses, after DNS, unless
    `allow_private` (`WEBHOOK_ALLOW_PRIVATE=true`, local previews and sandboxes only)."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsafeTarget("a webhook URL is http or https with a host")
    if allow_private:
        return
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise UnsafeTarget(f"cannot resolve {parts.hostname}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise UnsafeTarget(f"{parts.hostname} is a private address")
