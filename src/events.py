from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class JobBookedEvent:
    """Triggered when a new job is created/booked."""
    job_id: int
    customer_id: int
    business_id: int
    description: Optional[str] = None

@dataclass
class JobScheduledEvent:
    """Triggered when a job is assigned a schedule date/time."""
    job_id: int
    customer_id: int
    business_id: int
    scheduled_at: datetime

@dataclass
class OnMyWayEvent:
    """Triggered manually by a technician to notify the customer they are en route."""
    customer_id: int
    business_id: int
    eta_minutes: Optional[int] = None
