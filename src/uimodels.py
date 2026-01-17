from pydantic.v1 import BaseModel, Field, validator
from typing import Optional, List

# Allowlist for settings that can be updated via LLM
ALLOWED_SETTING_KEYS = ["confirm_by_default", "language", "timezone", "notifications"]


class LineItemInfo(BaseModel):
    """Information about a single line item."""

    description: str = Field(..., description="Description of the service or item")
    quantity: float = Field(1.0, description="Quantity or amount")
    unit_price: Optional[float] = Field(None, description="Price per unit")
    total_price: Optional[float] = Field(None, description="Total price for this line item")
    service_id: Optional[int] = Field(None, description="The ID of the matching service from the catalog")
    service_name: Optional[str] = Field(None, description="The canonical name of the service from the catalog")

    @validator("quantity", "unit_price", "total_price")
    def validate_non_negative(cls, v, field):
        if v is not None and v < 0:
            raise ValueError(f"{field.name} cannot be negative")
        if field.name == "quantity" and v is not None and v > 1_000_000:
            raise ValueError("Quantity is nonsensically high (> 1 million)")
        return v


class AddJobTool(BaseModel):
    """Add a new job.
    Triggered if a price, job description, or specific job task is supplied."""

    customer_name: str = Field(..., description="Name of the customer", max_length=100)
    customer_phone: Optional[str] = Field(
        None, description="Phone number of the customer", max_length=20
    )
    location: Optional[str] = Field(
        None, description="Address or location of the job", max_length=200
    )
    price: Optional[float] = Field(None, description="Total price or value of the job")
    description: Optional[str] = Field(
        None, description="Details of the work to be done", max_length=500
    )
    status: Optional[str] = Field(
        "pending", description="Status: 'pending', 'done', 'scheduled'"
    )
    line_items: Optional[List[LineItemInfo]] = Field(
        None, description="List of structured line items for the job"
    )

    @validator("price")
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v


class AddLeadTool(BaseModel):
    """Add a new lead, client, or customer without a job.
    Triggered when adding a person/entity without specific job details or 'request' keyword."""

    name: str = Field(..., description="Name of the customer/lead", max_length=100)
    phone: Optional[str] = Field(None, description="Phone number", max_length=20)
    street: Optional[str] = Field(
        None, description="Street address (e.g. 'High Street 44')", max_length=200
    )
    city: Optional[str] = Field(
        None, description="City (e.g. 'Dublin')", max_length=100
    )
    country: Optional[str] = Field(
        None, description="Country (e.g. 'Ireland')", max_length=100
    )
    location: Optional[str] = Field(
        None,
        description="Original full address string if parsing fails",
        max_length=200,
    )
    details: Optional[str] = Field(
        None,
        description="Additional details or description about the lead/client",
        max_length=500,
    )


class EditCustomerTool(BaseModel):
    """Update customer details like phone, address, or notes."""

    query: str = Field(
        ..., description="Name or phone to find the customer", max_length=100
    )
    name: Optional[str] = Field(None, description="New name", max_length=100)
    phone: Optional[str] = Field(None, description="New phone number", max_length=20)
    location: Optional[str] = Field(None, description="New address", max_length=200)
    details: Optional[str] = Field(
        None, description="New details/notes", max_length=500
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


class AddRequestTool(BaseModel):
    """Store a general request or note.
    ONLY triggered if user explicitly says 'add request' or similar."""

    content: str = Field(..., description="The content of the request or note")
    customer_name: Optional[str] = Field(
        None, description="Name of the customer if mentioned", max_length=100
    )
    customer_phone: Optional[str] = Field(
        None, description="Phone number of the customer if mentioned", max_length=20
    )
    time: str = Field(
        "anytime",
        description="Natural language time (e.g., 'tomorrow at 2pm', 'anytime')",
        max_length=100,
    )
    iso_time: Optional[str] = Field(
        None,
        description="ISO 8601 formatted datetime string (parsed by LLM)",
        max_length=50,
    )


class SearchTool(BaseModel):
    """Search for jobs, customers, or requests."""

    query: str = Field(
        ...,
        description="The search term (name, phone, job description, or 'all')",
        max_length=100,
    )
    entity_type: Optional[str] = Field(
        None,
        description="Filter by entity type: 'job', 'customer', 'request', 'lead'. If not specified, searches all.",
    )
    query_type: Optional[str] = Field(
        "general",
        description="Type of query: 'general' (text match), 'added' (created_at), 'scheduled' (scheduled_at). Defaults to 'general' if not time-based.",
    )
    min_date: Optional[str] = Field(
        None,
        description="Start date for range filtering in ISO format (YYYY-MM-DDTHH:MM:SS)",
    )
    max_date: Optional[str] = Field(
        None,
        description="End date for range filtering in ISO format (YYYY-MM-DDTHH:MM:SS)",
    )
    status: Optional[str] = Field(
        None, description="Filter by status (e.g., 'pending', 'done', 'completed')"
    )
    radius: Optional[float] = Field(
        None, description="Search radius in meters (default 200m if location provided)"
    )
    center_lat: Optional[float] = Field(
        None, description="Latitude for proximity search"
    )
    center_lon: Optional[float] = Field(
        None, description="Longitude for proximity search"
    )
    center_address: Optional[str] = Field(
        None, description="Address for proximity search (e.g., 'High Street 34')"
    )
    pipeline_stage: Optional[str] = Field(
        None, description="Filter by pipeline stage (e.g., 'not_contacted', 'lost')"
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


class GetPipelineTool(BaseModel):
    """Get a summary of the sales pipeline (funnel).
    Triggered when the user asks about the health of the business, pipeline status, or funnel."""

    ignore_me: str = Field("pipeline", description="Ignored field, default to 'pipeline'")


class UpdateCustomerStageTool(BaseModel):
    """Update a customer's pipeline stage manually.
    Triggered when user says 'Mark John as Lost', 'Customer is not interested', or similar."""

    query: str = Field(
        ..., description="Name or phone to find the customer", max_length=100
    )
    stage: str = Field(
        ...,
        description="The new pipeline stage: 'not_contacted', 'contacted', 'converted_once', 'converted_recurrent', 'not_interested', 'lost'",
    )


class AddServiceTool(BaseModel):
    """Add a new service to the catalog."""

    name: str = Field(..., description="Name of the service (e.g. 'Window Cleaning')")
    price: float = Field(..., description="Default price for the service")

    @validator("price")
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v


class EditServiceTool(BaseModel):
    """Edit an existing service."""

    original_name: str = Field(..., description="The name of the service to edit (to find it)")
    new_name: Optional[str] = Field(None, description="New name for the service")
    new_price: Optional[float] = Field(None, description="New default price")
    
    @validator("new_price")
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v


class DeleteServiceTool(BaseModel):
    """Delete a service from the catalog."""

    name: str = Field(..., description="Name of the service to delete")


class ListServicesTool(BaseModel):
    """List all available services."""
    pass


class ExitSettingsTool(BaseModel):
    """Exit the settings mode."""
    pass



