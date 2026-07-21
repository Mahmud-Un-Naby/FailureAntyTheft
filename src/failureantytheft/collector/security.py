"""Network-destination validation for user-supplied sensor URLs."""

import asyncio
import ipaddress
import socket
from collections.abc import Iterable
from urllib.parse import urlsplit


def _allowed_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if address.is_loopback or address.is_multicast or address.is_unspecified or address.is_reserved:
        return False
    return address.is_private or address.is_link_local


async def validate_sensor_url(url: str, *, allowed_ports: Iterable[int] = (80, 8080)) -> str:
    """Return a normalized base URL after scheme, port, and DNS/IP checks."""
    parsed = urlsplit(url)
    if parsed.scheme != "http":
        raise ValueError("sensor URL must use http")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("sensor URL cannot contain credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("sensor URL cannot contain a query or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("sensor URL must not contain a path")
    host = parsed.hostname
    if not host:
        raise ValueError("sensor URL requires a host")
    try:
        port = parsed.port or 80
    except ValueError as error:
        raise ValueError("sensor URL has an invalid port") from error
    allowed = set(allowed_ports)
    if port not in allowed:
        raise ValueError(f"sensor URL port {port} is not allowed")

    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address]
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        loop = asyncio.get_running_loop()
        results = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addresses = {ipaddress.ip_address(item[4][0]) for item in results}
    if not addresses or any(not _allowed_address(address) for address in addresses):
        raise ValueError("sensor URL must resolve only to private or link-local addresses")
    display_host = f"[{host}]" if ":" in host else host
    return f"http://{display_host}:{port}"


__all__ = ["validate_sensor_url"]
