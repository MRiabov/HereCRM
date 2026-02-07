import time
from collections import defaultdict
from typing import Dict, List
from urllib.parse import urlparse
from src.config import settings

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
    Validates a redirect URL to prevent Open Redirect vulnerabilities.

    Allowed URLs:
    - Relative paths (starting with / but not //)
    - Absolute URLs pointing to localhost/127.0.0.1
    - Absolute URLs matching origins in settings.allowed_origins (if not *)

    Returns the URL if safe, otherwise returns '/'.
    """
    if not url:
        return "/"

    try:
        # Prevent protocol-relative URLs (e.g., //evil.com)
        if url.startswith("//"):
             return "/"

        parsed = urlparse(url)

        # If no scheme/netloc, treat as relative path
        if not parsed.scheme and not parsed.netloc:
             if url.startswith("/"):
                  return url
             # If it doesn't start with /, force safe fallback
             return "/"

        # If absolute URL, validate scheme and netloc
        if parsed.scheme not in ("http", "https"):
             return "/"

        hostname = parsed.hostname
        if not hostname:
             return "/"

        # Allow localhost
        if hostname in ("localhost", "127.0.0.1") or hostname.endswith(".localhost"):
             return url

        # Allow configured origins
        allowed_origins = getattr(settings, "allowed_origins", [])
        if allowed_origins and "*" not in allowed_origins:
             # Check if origin matches any allowed origin
             origin = f"{parsed.scheme}://{parsed.netloc}"
             if origin in allowed_origins:
                  return url

        return "/"
    except Exception:
        return "/"
