import time
from collections import defaultdict
from typing import Dict, List
from urllib.parse import urlparse

# Simple in-memory rate limiter: {phone_number: [last_request_times]}
# Defaults to 10 requests per 60 seconds per phone number
_rate_limit_data: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(phone: str, limit: int = 10, window: int = 60) -> bool:
    """
    Checks if a phone number is rate limited.
    Returns True if limited, False otherwise.
    """
    now = time.time()
    # Clean up old timestamps
    _rate_limit_data[phone] = [t for t in _rate_limit_data[phone] if now - t < window]

    if len(_rate_limit_data[phone]) >= limit:
        return True

    _rate_limit_data[phone].append(now)
    return False


def validate_redirect_url(url: str) -> str:
    """
    Validates the redirect URL to prevent Open Redirect vulnerabilities.
    Returns the URL if safe, otherwise raises ValueError.

    Safe means:
    - Relative URL (starts with /) but not protocol-relative (//)
    - Or matches allowed local dev domains (localhost, 127.0.0.1)
    """
    if not url:
        return "/"

    # Use urlparse to inspect components
    parsed = urlparse(url)

    # Check for absolute URLs (with scheme or netloc)
    if parsed.scheme or parsed.netloc:
        # Only allow localhost/127.0.0.1 for development redirection flows
        if parsed.hostname in ["localhost", "127.0.0.1"]:
            return url
        raise ValueError("External redirects are not allowed")

    # Check for protocol-relative URLs (start with //) which are dangerous
    # urlparse might not set netloc if scheme is missing but it starts with // depending on version/context,
    # but usually //example.com -> netloc='example.com'
    # However, to be safe against edge cases:
    if url.strip().startswith("//"):
        raise ValueError("Protocol-relative redirects are not allowed")

    # Ensure relative path starts with /
    if not url.startswith("/"):
        return "/" + url

    return url
