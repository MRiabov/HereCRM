from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel

# --- Shared / Base Schemas ---

class UserSchema(BaseModel):
    id: int
    name: Optional[str]
    email: Optional[str]
    phone_number: Optional[str]
    role: str
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    location_updated_at: Optional[datetime] = None
    default_start_location_lat: Optional[float] = None
    default_start_location_lng: Optional[float] = None

    class Config:
        from_attributes = True

class CustomerSchema(BaseModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pipeline_stage: str

    class Config:
        from_attributes = True

class LineItemSchema(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price: float
    total_price: float
    service_id: Optional[int] = None

    class Config:
        from_attributes = True

class JobSchema(BaseModel):
    id: int
    description: Optional[str]
    status: str
    scheduled_at: Optional[datetime]
    value: Optional[float]
    location: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    paid: bool = False
    estimated_duration: int = 60
    customer: Optional[CustomerSchema]
    employee: Optional[UserSchema] = None
    line_items: List[LineItemSchema] = []

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
    description: Optional[str] = None
    status: str = "pending"
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = None
    location: Optional[str] = None
    estimated_duration: int = 60

class JobUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = None
    employee_id: Optional[int] = None
    estimated_duration: Optional[int] = None

# --- Chat Schemas ---

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime
    is_outbound: bool

class ChatSendRequest(BaseModel):
    customer_id: int
    message: str

class ChatExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

# --- Customer Schemas ---

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    pipeline_stage: Optional[str] = None

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

# --- Quote Schemas ---

class QuoteLineItemSchema(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price: float
    total: float
    service_id: Optional[int] = None

    class Config:
        from_attributes = True

class QuoteSchema(BaseModel):
    id: int
    customer_id: int
    total_amount: float
    status: str
    external_token: str
    public_url: Optional[str]
    created_at: datetime
    items: List[QuoteLineItemSchema] = []
    customer: Optional[CustomerSchema] = None

    class Config:
        from_attributes = True

class QuoteCreate(BaseModel):
    customer_id: int
    items: List[dict] # Simplified for creation
    status: str = "draft"

# --- Request Schemas ---

class RequestSchema(BaseModel):
    id: int
    content: str
    status: str
    created_at: datetime
    customer_id: Optional[int] = None # Inferred from context usually
    
    class Config:
        from_attributes = True

# --- Service Catalog Schemas ---

class ServiceSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    default_price: float
    estimated_duration: int
    
    class Config:
        from_attributes = True

class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_price: float
    estimated_duration: int = 60

# --- Finance Schemas ---

class ExpenseSchema(BaseModel):
    id: int
    description: Optional[str] = None
    category: str
    amount: float
    created_at: datetime
    receipt_url: Optional[str] = None
    job_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class LedgerEntrySchema(BaseModel):
    id: int
    employee_id: int
    amount: float
    type: str # credit/debit
    description: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Settings & Workflow ---

class BusinessSettingsSchema(BaseModel):
    workflow_invoicing: Optional[str]
    workflow_quoting: Optional[str]
    workflow_payment_timing: Optional[str]
    workflow_tax_inclusive: Optional[bool]
    workflow_include_payment_terms: Optional[bool]
    workflow_enable_reminders: Optional[bool]
    payment_link: Optional[str]
    default_city: Optional[str] = None
    default_country: Optional[str] = None
    quickbooks_connected: bool
    quickbooks_last_sync: Optional[datetime] = None
    stripe_connected: bool
    seat_count: int
    billing_cycle_anchor: Optional[datetime] = None

class BusinessSettingsUpdate(BaseModel):
    workflow_invoicing: Optional[str] = None
    workflow_quoting: Optional[str] = None
    workflow_payment_timing: Optional[str] = None
    workflow_tax_inclusive: Optional[bool] = None
    workflow_include_payment_terms: Optional[bool] = None
    workflow_enable_reminders: Optional[bool] = None
    payment_link: Optional[str] = None
    default_city: Optional[str] = None
    default_country: Optional[str] = None

# --- Search ---

class SearchResult(BaseModel):
    type: str # customer, job, request
    id: int
    title: str
    subtitle: Optional[str]
    metadata: Optional[Dict[str, Any]] = None

class GlobalSearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

# --- Routing Schemas ---

class RoutingStep(BaseModel):
    job_id: int
    arrival_time: Optional[datetime]
    departure_time: Optional[datetime]
    distance_to_next: Optional[float] = None
    duration_to_next: Optional[float] = None
    job: JobSchema

class RouteSchema(BaseModel):
    employee_id: int
    employee_name: str
    steps: List[RoutingStep]

class RoutingMetrics(BaseModel):
    total_distance: float # meters
    total_duration: float # seconds
    jobs_assigned: int
    unassigned_count: int

class RoutingResponse(BaseModel):
    date: str
    metrics: RoutingMetrics
    routes: List[RouteSchema]
    unassigned_jobs: List[JobSchema]

class GeocodeResponse(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    street: Optional[str]
    city: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    full_address: Optional[str]

