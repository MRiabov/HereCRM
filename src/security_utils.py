import time
from collections import defaultdict
from typing import Dict, List

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
