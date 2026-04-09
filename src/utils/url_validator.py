import asyncio
import ipaddress
from urllib.parse import urlparse
import logging
import socket

logger = logging.getLogger(__name__)

async def validate_safe_url(url: str) -> None:
    """
    Validates that a URL is safe to request.
    Raises ValueError if the URL is unsafe (e.g., points to internal network).
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValueError(f"Invalid URL format: {e}")

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https schemes are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must have a hostname")

    # Check if hostname is an IP address
    ip = None
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP address, needs resolution
        pass

    if ip:
        if _is_unsafe_ip(ip):
            raise ValueError(f"Restricted IP address: {hostname}")
        return

    # If we are here, it's not an IP, so we must resolve it
    try:
        loop = asyncio.get_running_loop()
        # loop.getaddrinfo returns a list of (family, type, proto, canonname, sockaddr)
        addr_infos = await loop.getaddrinfo(hostname, None)

        for family, type, proto, canonname, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            if _is_unsafe_ip(ip):
                raise ValueError(f"Hostname resolved to restricted IP: {ip_str}")

    except socket.gaierror as e:
        raise ValueError(f"Could not resolve hostname: {hostname}") from e
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        logger.error(f"Error validating URL: {e}")
        raise ValueError(f"Error validating URL: {e}")

def _is_unsafe_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    return (
        ip.is_loopback or
        ip.is_private or
        ip.is_reserved or
        ip.is_link_local or
        ip.is_multicast or
        str(ip) == "0.0.0.0"
    )
