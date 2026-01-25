from typing import Optional, List, ClassVar
from pydantic.v1 import BaseModel, Field, validator

# Allowlist for settings that can be updated via LLM
ALLOWED_SETTING_KEYS = ["confirm_by_default", "language", "timezone", "notifications", "default_city", "default_country"]


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
        None, description="Address or location of the job (e.g. 'High Street 44')", max_length=200
    )
    city: Optional[str] = Field(
        None, description="City (e.g. 'Dublin')", max_length=100
    )
    country: Optional[str] = Field(
        None, description="Country (e.g. 'Ireland')", max_length=100
    )
    price: Optional[float] = Field(None, description="Total price or value of the job")
    description: Optional[str] = Field(
        None, description="Details of the work to be done", max_length=500
    )
    status: Optional[str] = Field(
        None, description="Status: 'pending', 'done', 'scheduled'"
    )
    line_items: Optional[List[LineItemInfo]] = Field(
        None, description="List of structured line items for the job"
    )
    time: Optional[str] = Field(
        None,
        description="Natural language time (e.g., 'Tuesday 2pm', 'tomorrow')",
        max_length=100,
    )
    iso_time: Optional[str] = Field(
        None,
        description="ISO 8601 formatted datetime string (parsed by LLM)",
        max_length=50,
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
    city: Optional[str] = Field(
        None, description="City (e.g. 'Dublin')", max_length=100
    )
    country: Optional[str] = Field(
        None, description="Country (e.g. 'Ireland')", max_length=100
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
    detailed: bool = False
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
        ..., description="Action to perform: 'schedule', 'complete', 'log', or 'quote'"
    )
    time: Optional[str] = Field(
        None, description="Optional time for scheduling or reminders"
    )
    iso_time: Optional[str] = Field(
        None, description="ISO 8601 formatted datetime string (parsed by LLM)"
    )



class SendStatusTool(BaseModel):
    """Send a status update message to a customer (e.g. 'On my way', 'Running late')."""

    query: str = Field(
        ...,
        description="Name or phone to find the customer (or 'next_scheduled_client')",
        max_length=100,
    )
    status_type: str = Field(
        "on_way",
        description="Type of status: 'on_way', 'running_late', 'start_job', 'finish_job'",
    )
    message_content: Optional[str] = Field(
        None,
        description="Optional custom message content (e.g. 'running 10 mins late')",
        max_length=500,
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

class ExportQueryTool(BaseModel):
    """Export data based on a natural language query."""

    query: str = Field(..., description="The specific keywords to search for (e.g., 'Dublin' if the user says 'customers in Dublin', or 'all' for everything).")
    format: str = Field("csv", description="The desired output format: 'csv', 'excel', or 'json'.")
    entity_type: Optional[str] = Field(None, description="Type of entity to export: 'customer', 'job', 'lead'. If unspecified, infer from query or default to customer.")
    status: Optional[str] = Field(None, description="Filter by status or pipeline stage (e.g., 'pending', 'lost', 'completed').")
    min_date: Optional[str] = Field(None, description="Start date for filtering in ISO 8601 format.")
    max_date: Optional[str] = Field(None, description="End date for filtering in ISO 8601 format.")

    @validator("format")
    def validate_format(cls, v):
        if v.lower() not in ["csv", "excel", "json"]:
            return "csv" # Default to csv if invalid
        return v.lower()

class GetBillingStatusTool(BaseModel):
    """Check the current subscription status, limits, and usage.
    Triggered when user asks about 'billing', 'subscription', 'plan', or 'limits'."""
    pass


class RequestUpgradeTool(BaseModel):
    """Request an upgrade for seats or addons.
    Triggered when user wants to 'buy seats', 'add user limit', 'purchase addon', or 'upgrade plan'."""
    
    item_type: str = Field(..., description="Type of item: 'seat', 'addon', or 'messaging'")
    item_id: Optional[str] = Field(None, description="Specific addon ID if type is 'addon' (e.g., 'campaign_manager'). Leave empty for seats.")
    quantity: int = Field(1, description="Number of items to add")

    @validator("item_type")
    def validate_type(cls, v):
        if v not in ["seat", "addon", "messaging"]:
            raise ValueError("item_type must be 'seat', 'addon', or 'messaging'")
        return v


class ProServiceTool(BaseModel):
    """A premium tool for Pro businesses only."""
    required_scope: ClassVar[str] = "pro_features"
    pass

class ExitDataManagementTool(BaseModel):
    """Exit the data management mode."""
    pass






class MassEmailTool(BaseModel):

    """Send a mass email or message to multiple customers.
    Requires 'campaigns' addon."""
    required_scope: ClassVar[str] = "campaigns"
    subject: str = Field(..., description="Subject of the email")
    body: str = Field(..., description="Content of the message")
    recipient_query: str = Field("all", description="Filter for recipients (e.g. 'all', 'Dublin customers')")

class ManageEmployeesTool(BaseModel):
    """Access employee management features (shifts, roles).
    Requires 'manage_employees' addon."""
    required_scope: ClassVar[str] = "manage_employees"
    action: str = Field(..., description="Action: 'list', 'assign_shift', 'view_availability'")
    details: Optional[str] = Field(None, description="Details for the action")


class QuoteLineItemInput(BaseModel):
    """A single line item in a quote."""
    description: str = Field(..., description="Description of the service or item")
    quantity: float = Field(1.0, description="Quantity or amount")
    price: float = Field(..., description="Price per unit")

    @validator("quantity", "price")
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError("Must be non-negative")
        return v


class CreateQuoteTool(BaseModel):
    """Create and send a quote to a customer.
    Triggered when user wants to 'send a quote', 'create proposal', or 'give price'."""
    customer_identifier: str = Field(..., description="Name or Phone of the customer to find.")
    items: List[QuoteLineItemInput] = Field(..., description="List of items in the quote")
class LocateEmployeeTool(BaseModel):
    """Locate an employee or list location of all employees.
    Triggered when admin/dispatcher asks 'Where is John?' or 'Where are my techs?'."""
    employee_name: Optional[str] = Field(
        None, description="Name of the employee to locate. If omitted, lists all."
    )


class CheckETATool(BaseModel):
    """Check the estimated time of arrival for a technician to a customer.
    Triggered when customer asks 'When will you arrive?', 'Where is the tech?', 'ETA'."""
    customer_query: Optional[str] = Field(
        None, description="Name/Phone of customer if admin is asking. If customer asks, leave empty to use sender."
    )


class AutorouteTool(BaseModel):
    """Preview or execute automatic job routing to minimize distance and maximize jobs.
    Triggered when user says 'autoroute', 'optimize schedule', or 'plan my day'."""
    date: Optional[str] = Field(None, description="The date to optimize for (YYYY-MM-DD). Defaults to today.")
    apply: bool = Field(False, description="If True, applies the schedule and assigns jobs to technicians.")
    notify: bool = Field(True, description="If True (and apply is True), notifies technicians and customers.")


class ConnectQuickBooksTool(BaseModel):
    """Initiate the connection to QuickBooks Online.
    Triggered when user says 'Connect QuickBooks' or 'Link Accounting'."""
    pass


class DisconnectQuickBooksTool(BaseModel):
    """Disconnect the currently linked QuickBooks Online account.
    Triggered when user says 'Disconnect QuickBooks'."""
    pass


class QuickBooksStatusTool(BaseModel):
    """Check the status of the QuickBooks integration and last sync details.
    Triggered when user says 'QuickBooks status', 'Accounting status', or 'Check sync'."""
    pass


class SyncQuickBooksTool(BaseModel):
    """Manually trigger a synchronization with QuickBooks.
    Triggered when user says 'Sync QuickBooks now', 'Push to QuickBooks', or 'Update accounting'."""
    pass


class GetWorkflowSettingsTool(BaseModel):
    """Retrieve the current business workflow configuration (invoicing, quoting, payments).
    Triggered when user asks 'what are my workflow settings', 'how is my quoting set up', etc."""
    pass


class UpdateWorkflowSettingsTool(BaseModel):
    """Update the business workflow configuration.
    Allowed values for invoicing/quoting: 'never', 'manual', 'automatic'.
    Allowed values for payment_timing: 'always_paid_on_spot', 'usually_paid_on_spot', 'paid_later'."""

    invoicing: Optional[str] = Field(None, description="Invoicing workflow: 'never', 'manual', 'automatic'")
    quoting: Optional[str] = Field(None, description="Quoting workflow: 'never', 'manual', 'automatic'")
    payment_timing: Optional[str] = Field(None, description="Payment timing: 'always_paid_on_spot', 'usually_paid_on_spot', 'paid_later'")
    tax_inclusive: Optional[bool] = Field(None, description="Whether prices include tax")
    include_payment_terms: Optional[bool] = Field(None, description="Whether to show net terms on invoices")
    enable_reminders: Optional[bool] = Field(None, description="Whether to send auto-reminders")


class ExitAccountingTool(BaseModel):
    """Exit the accounting management mode."""
    pass


class ConnectGoogleCalendarTool(BaseModel):
    """Initiate the connection to Google Calendar.
    Triggered when user says 'Connect Google Calendar' or 'Sync my calendar'."""
    pass


class DisconnectGoogleCalendarTool(BaseModel):
    """Disconnect the currently linked Google Calendar.
    Triggered when user says 'Disconnect Google Calendar'."""
    pass


class GoogleCalendarStatusTool(BaseModel):
    """Check the status of Google Calendar integration.
    Triggered when user says 'Google Calendar status' or 'Check calendar connection'."""
    pass


class CheckInTool(BaseModel):
    """Check in for the day/shift. 
    Triggered when user says 'Start shift', 'Check in', 'I am here'."""
    pass

class CheckOutTool(BaseModel):
    """Check out for the day/shift.
    Triggered when user says 'End shift', 'Check out', 'I am leaving'."""
    pass

class StartJobTool(BaseModel):
    """Start tracking time for a specific job.
    Triggered when user says 'Start job', 'I am arriving at [customer]', 'Begin work'."""
    job_id: int = Field(..., description="ID of the job to start.")

class FinishJobTool(BaseModel):
    """Finish tracking time for a specific job.
    Triggered when user says 'Finish job', 'Job done', 'Work complete'."""
    job_id: int = Field(..., description="ID of the job to finish.")


class AddExpenseTool(BaseModel):
    """Record a business expense (e.g., fuel, materials, parking).
    Triggered when user says 'Add expense', 'Log cost', 'I spent $X on [item]'."""

    amount: float = Field(..., description="The amount spent")
    description: str = Field(..., description="What was the expense for?")
    category: str = Field("General", description="Expense category (e.g., Fuel, Supplies, Parking)")
    job_id: Optional[int] = Field(None, description="The ID of the job this expense is linked to, if any")

    @validator("amount")
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
