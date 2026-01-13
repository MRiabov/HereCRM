from pydantic import BaseModel, Field
from typing import Optional

class AddJobTool(BaseModel):
    """Add a new job/work order for a customer."""
    customer_name: str = Field(..., description="Name of the customer")
    customer_phone: Optional[str] = Field(None, description="Phone number of the customer")
    location: Optional[str] = Field(None, description="Address or location of the job")
    price: Optional[float] = Field(None, description="Price or value of the job")
    description: str = Field(..., description="Details of the work to be done")

class ScheduleJobTool(BaseModel):
    """Schedule an existing or new job for a specific time."""
    job_id: Optional[int] = Field(None, description="ID of the job if known")
    customer_query: Optional[str] = Field(None, description="Name or phone to find the customer/job")
    time: str = Field(..., description="Natural language time (e.g., 'Tuesday 2pm', 'tomorrow')")

class StoreRequestTool(BaseModel):
    """Store a general request or note from a customer that isn't a job yet."""
    content: str = Field(..., description="The content of the request or note")

class SearchTool(BaseModel):
    """Search for jobs, customers, or requests."""
    query: str = Field(..., description="The search term (name, phone, or job description)")

class UpdateSettingsTool(BaseModel):
    """Update user preferences or business settings."""
    setting_key: str = Field(..., description="The setting to change (e.g., 'confirm_by_default')")
    setting_value: str = Field(..., description="The new value for the setting")

class ConvertRequestTool(BaseModel):
    """Convert a general request or a query into a specific action like scheduling or logging."""
    query: str = Field(..., description="Name, phone number or content to identifying the entity")
    action: str = Field(..., description="Action to perform: 'schedule', 'complete', or 'log'")
    time: Optional[str] = Field(None, description="Optional time for the action")
