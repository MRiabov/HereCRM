from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from src.models import MessageRole, Job, Customer, Invoice, User

# --- Shared / Base Schemas ---

class UserSchema(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    role: str

    class Config:
        from_attributes = True

class CustomerSchema(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    pipeline_stage: str

    class Config:
        from_attributes = True

class JobSchema(BaseModel):
    id: int
    description: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    value: Optional[float]
    location: Optional[str]
    customer: Optional[CustomerSchema]
    employee: Optional[UserSchema] = None

    class Config:
        from_attributes = True

# --- Dashboard Schemas ---

class DashboardStats(BaseModel):
    revenue_monthly: float
    active_leads_count: int
    leads_need_followup: int
    pipeline_breakdown: Dict[str, Any]

class RecentActivity(BaseModel):
    type: str # 'invoice', 'lead', 'job'
    title: str
    description: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

# --- Job Schemas ---

class JobListResponse(BaseModel):
    date: str # YYYY-MM-DD
    jobs: List[JobSchema]

class JobCreate(BaseModel):
    customer_id: int
    description: str
    status: str = "pending"
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = None
    location: Optional[str] = None

class JobUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = None
    employee_id: Optional[int] = None

# --- Chat Schemas ---

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    is_outbound: bool

class ChatSendRequest(BaseModel):
    customer_id: int
    message: str

# --- Customer Schemas ---

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None

# --- Invoice Schemas ---

class InvoiceSchema(BaseModel):
    id: int
    job_id: int
    total_amount: float
    status: str
    created_at: datetime
    public_url: str
    customer_name: Optional[str] = None # Enriched

    class Config:
        from_attributes = True
