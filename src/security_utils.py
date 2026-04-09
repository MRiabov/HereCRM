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
    Validates a redirect URL to prevent Open Redirect vulnerabilities.
    Only allows relative URLs or URLs matching localhost/127.0.0.1 (for dev).
    Returns "/" if the URL is invalid.
    """
    if not url:
        return "/"

    try:
        parsed = urlparse(url)
        # If no netloc (scheme-less), it's relative. But check for protocol-relative "//"
        # CRITICAL: We must also check that there is NO scheme (e.g. javascript:, http:)
        if not parsed.netloc and not parsed.scheme:
             # Prevent "//evil.com" which is protocol-relative
             if url.strip().startswith("//") or "\\" in url:
                 return "/"
             return url

        # Allow localhost/127.0.0.1 for development
        if parsed.hostname in ["localhost", "127.0.0.1"]:
            return url

        # Deny everything else
        return "/"
    except Exception:
        return "/"
