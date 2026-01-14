from pydantic.v1 import BaseModel, Field, validator
from typing import Optional

# Allowlist for settings that can be updated via LLM
ALLOWED_SETTING_KEYS = ["confirm_by_default", "language", "timezone", "notifications"]


class AddJobTool(BaseModel):
    """Add a new job, lead, client, or customer.
    Triggered if a price tag or job description is supplied,
    or if adding a person/entity without specific 'request' keyword."""

    customer_name: str = Field(..., description="Name of the customer", max_length=100)
    customer_phone: Optional[str] = Field(
        None, description="Phone number of the customer", max_length=20
    )
    location: Optional[str] = Field(
        None, description="Address or location of the job", max_length=200
    )
    price: Optional[float] = Field(None, description="Price or value of the job")
    description: Optional[str] = Field(
        None, description="Details of the work to be done", max_length=500
    )
    category: Optional[str] = Field(
        "job", description="Category: job, lead, client, customer"
    )
    status: Optional[str] = Field(
        "pending", description="Status: 'pending', 'done', 'scheduled'"
    )


class ScheduleJobTool(BaseModel):
    """Schedule an existing or new job for a specific time.
    Triggered if 'schedule' is used or a specific time/date in the future is supplied."""

    job_id: Optional[int] = Field(None, description="ID of the job if known")
    customer_query: Optional[str] = Field(
        None, description="Name or phone to find the customer/job", max_length=100
    )
    time: str = Field(
        ...,
        description="Natural language time (e.g., 'Tuesday 2pm', 'tomorrow')",
        max_length=100,
    )
    iso_time: Optional[str] = Field(
        None,
        description="ISO 8601 formatted datetime string (parsed by LLM)",
        max_length=50,
    )


class StoreRequestTool(BaseModel):
    """Store a general request or note.
    ONLY triggered if user explicitly says 'add request' or similar."""

    content: str = Field(..., description="The content of the request or note")
    customer_name: Optional[str] = Field(
        None, description="Name of the customer if mentioned", max_length=100
    )
    customer_phone: Optional[str] = Field(
        None, description="Phone number of the customer if mentioned", max_length=20
    )


class SearchTool(BaseModel):
    """Search for jobs, customers, or requests."""

    query: str = Field(
        ...,
        description="The search term (name, phone, or job description)",
        max_length=100,
    )


class UpdateSettingsTool(BaseModel):
    """Update user preferences or business settings."""

    setting_key: str = Field(
        ...,
        description="The setting to change (e.g., 'confirm_by_default')",
        max_length=50,
    )
    setting_value: str = Field(
        ..., description="The new value for the setting", max_length=100
    )

    @validator("setting_key")
    def validate_key(cls, v):
        if v not in ALLOWED_SETTING_KEYS:
            raise ValueError(f"Setting key '{v}' is not allowed.")
        return v


class ConvertRequestTool(BaseModel):
    """Convert a general request or a query into a specific action like scheduling or logging."""

    query: str = Field(
        ..., description="Name, phone number or content to identifying the entity"
    )
    action: str = Field(
        ..., description="Action to perform: 'schedule', 'complete', or 'log'"
    )
    time: Optional[str] = Field(
        None, description="Optional time for scheduling or reminders"
    )
    iso_time: Optional[str] = Field(
        None, description="ISO 8601 formatted datetime string (parsed by LLM)"
    )


class HelpTool(BaseModel):
    """Get help or information about available commands."""

    pass
