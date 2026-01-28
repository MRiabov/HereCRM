from src.models import Urgency
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field, AnyHttpUrl
from src.models import (
    JobStatus, PipelineStage, InvoicingWorkflow, QuotingWorkflow, 
    PaymentTiming, JobCreationDefault, WageModelType, LedgerEntryType,
    QuoteStatus, QuickBooksSyncStatus, SyncType, SyncLogStatus,
    CampaignStatus, CampaignChannel, WhatsAppTemplateStatus, WhatsAppTemplateCategory,
    InvoiceStatus, ExportStatus, ExportFormat, RequestStatus, UserRole, MessageRole
)
from enum import Enum

# --- Constants ---
PHONE_PATTERN = r"(^\+?[1-9]\d{1,14}$|^$)"
EMAIL_PATTERN = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$|^$)"

# --- Shared / Base Schemas ---

class WageConfigurationSchema(BaseModel):
    model_type: WageModelType
    rate_value: float
    tax_withholding_rate: float
    allow_expense_claims: bool

    model_config = ConfigDict(from_attributes=True)

class UserSchema(BaseModel):
    id: int
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    phone_number: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    role: UserRole
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    location_updated_at: Optional[datetime] = None
    default_start_location_lat: Optional[float] = None
    default_start_location_lng: Optional[float] = None
    wage_config: Optional[WageConfigurationSchema] = None

    model_config = ConfigDict(from_attributes=True)

class CustomerSchema(BaseModel):
    id: int
    name: Optional[str] = Field(None, max_length=200)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    street: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pipeline_stage: PipelineStage
    job_count: int = 0
    total_value: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class LineItemSchema(BaseModel):
    id: int
    description: str = Field(..., max_length=500)
    quantity: float
    unit_price: float
    total_price: float
    service_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class LineItemCreate(BaseModel):
    description: str = Field(..., max_length=500)
    quantity: float = 1.0
    unit_price: float
    service_id: Optional[int] = None

class JobSchema(BaseModel):
    id: int
    description: Optional[str] = Field(None, max_length=1000)
    status: JobStatus
    scheduled_at: Optional[datetime]
    value: Optional[float]
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    paid: bool = False
    estimated_duration: int = 60
    begun_at: Optional[datetime] = None
    total_actual_duration_seconds: int = 0
    customer: Optional[CustomerSchema]
    employee: Optional[UserSchema] = None
    line_items: List[LineItemSchema] = []

    model_config = ConfigDict(from_attributes=True)

# --- Dashboard Schemas ---

class DashboardStats(BaseModel):
    revenue_monthly: float
    active_leads_count: int
    leads_need_followup: int
    pipeline_breakdown: Dict[str, Any]

class ActivityType(str, Enum):
    INVOICE = "invoice"
    JOB = "job"
    LEAD = "lead"

class RecentActivity(BaseModel):
    type: ActivityType # 'invoice', 'lead', 'job'
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=500)
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

# --- Job Schemas ---

class JobListResponse(BaseModel):
    date: str = Field(..., max_length=10) # YYYY-MM-DD
    jobs: List[JobSchema]

class JobCreate(BaseModel):
    customer_id: int
    description: Optional[str] = Field(None, max_length=1000)
    status: JobStatus = JobStatus.pending
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = None
    location: Optional[str] = Field(None, max_length=255)
    employee_id: Optional[int] = None
    estimated_duration: Optional[int] = None # Optional now, will be auto-calculated if items provided
    postal_code: Optional[str] = Field(None, max_length=20)
    items: Optional[List[LineItemCreate]] = None

class JobUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[JobStatus] = None
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = None
    employee_id: Optional[int] = None
    estimated_duration: Optional[int] = None
    location: Optional[str] = Field(None, max_length=255)
    postal_code: Optional[str] = Field(None, max_length=20)
    items: Optional[List[LineItemCreate]] = None

# --- Chat Schemas ---

class ChatMessage(BaseModel):
    id: Optional[int] = None
    role: MessageRole
    content: str = Field(..., max_length=5000)
    timestamp: datetime
    is_outbound: bool
    is_executed: bool = False

class ChatMessageUpdate(BaseModel):
    message: str = Field(..., max_length=5000)

class ChatSendRequest(BaseModel):
    customer_id: int
    message: str = Field(..., max_length=5000)
    retry_id: Optional[str] = Field(None, max_length=100)

class ChatExecuteRequest(BaseModel):
    tool_name: str = Field(..., max_length=100)
    arguments: Dict[str, Any]

# --- Customer Schemas ---

class CustomerCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    street: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    pipeline_stage: Optional[PipelineStage] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    street: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    pipeline_stage: Optional[PipelineStage] = None

class InvoiceSchema(BaseModel):
    id: int
    job_id: int
    total_amount: float
    status: InvoiceStatus
    created_at: datetime
    public_url: str = Field(..., max_length=500)
    customer_name: Optional[str] = Field(None, max_length=200) # Enriched

    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):
    job_id: int
    force_regenerate: bool = False
    invoice_number: Optional[str] = None
    issued_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    items: Optional[List[LineItemCreate]] = None

# --- Quote Schemas ---

class QuoteLineItemSchema(BaseModel):
    id: int
    description: str = Field(..., max_length=500)
    quantity: float
    unit_price: float
    total: float
    service_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class QuoteSchema(BaseModel):
    id: int
    customer_id: int
    total_amount: float
    status: QuoteStatus
    external_token: str = Field(..., max_length=100)
    public_url: Optional[str] = Field(None, max_length=500)
    created_at: datetime
    items: List[QuoteLineItemSchema] = []
    customer: Optional[CustomerSchema] = None

    model_config = ConfigDict(from_attributes=True)

class QuoteCreate(BaseModel):
    customer_id: int
    title: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)
    items: List[dict] # Simplified for creation
    total_amount: Optional[float] = None
    status: QuoteStatus = QuoteStatus.DRAFT

# --- Request Schemas ---

class RequestSchema(BaseModel):
    id: int
    description: str = Field(..., max_length=2000)
    status: RequestStatus
    urgency: Urgency
    expected_value: Optional[float] = None
    subtotal: float = 0.0
    tax_amount: float = 0.0
    tax_rate: float = 0.0
    follow_up_date: Optional[datetime] = None
    customer_id: Optional[int] = None
    customer_details: Optional[Dict[str, Any]] = None
    created_at: datetime
    customer: Optional[CustomerSchema] = None
    line_items: List[LineItemSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class RequestCreate(BaseModel):
    customer_id: Optional[int] = None
    description: str = Field(..., max_length=2000)
    urgency: Urgency = Urgency.MEDIUM
    expected_value: Optional[float] = None
    subtotal: Optional[float] = 0.0
    tax_amount: Optional[float] = 0.0
    tax_rate: Optional[float] = 0.0
    items: Optional[List[LineItemCreate]] = None
    follow_up_date: Optional[datetime] = None
    customer_details: Optional[Dict[str, Any]] = None

class RequestUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[RequestStatus] = None
    urgency: Optional[Urgency] = None
    expected_value: Optional[float] = None
    subtotal: Optional[float] = None
    tax_amount: Optional[float] = None
    tax_rate: Optional[float] = None
    items: Optional[List[LineItemCreate]] = None
    follow_up_date: Optional[datetime] = None
    customer_id: Optional[int] = None

# --- Service Catalog Schemas ---

class ServiceSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_price: float
    estimated_duration: int
    
    model_config = ConfigDict(from_attributes=True)

class ServiceCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_price: float
    estimated_duration: int = 60

# --- Finance Schemas ---

class ExpenseSchema(BaseModel):
    id: int
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field(..., max_length=100)
    amount: float
    created_at: datetime
    receipt_url: Optional[str] = Field(None, max_length=500)
    job_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class ExpenseCreate(BaseModel):
    amount: float
    category: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    job_id: Optional[int] = None
    vendor: Optional[str] = Field(None, max_length=100)
    date: Optional[datetime] = None

class LedgerEntrySchema(BaseModel):
    id: int
    employee_id: int
    amount: float
    type: str = Field(..., max_length=20) # credit/debit
    description: str = Field(..., max_length=500)
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- Settings & Workflow ---

class BusinessSettingsSchema(BaseModel):
    workflow_invoicing: Optional[InvoicingWorkflow]
    workflow_quoting: Optional[QuotingWorkflow]
    workflow_payment_timing: Optional[PaymentTiming]
    workflow_tax_inclusive: Optional[bool]
    workflow_include_payment_terms: Optional[bool]
    workflow_enable_reminders: Optional[bool]
    workflow_show_whatsapp_button: Optional[bool]
    workflow_pipeline_quoted_stage: bool
    workflow_job_creation_default: Optional[JobCreationDefault] = JobCreationDefault.UNSCHEDULED
    workflow_distance_unit: Optional[str] = Field("mi", max_length=10)
    workflow_auto_quote_followup: bool
    workflow_quote_followup_delay_hrs: int
    workflow_auto_review_requests: bool
    workflow_review_request_delay_hrs: int
    workflow_review_link: Optional[AnyHttpUrl] = None
    payment_link: Optional[AnyHttpUrl] = None
    default_city: Optional[str] = Field(None, max_length=100)
    default_country: Optional[str] = Field(None, max_length=100)
    default_tax_rate: Optional[float] = 0.0
    quickbooks_connected: bool
    quickbooks_last_sync: Optional[datetime] = None
    stripe_connected: bool
    seat_count: int
    invite_code: Optional[str] = Field(None, max_length=50)
    billing_cycle_anchor: Optional[datetime] = None
    marketing_settings: Optional[Dict[str, Any]] = None

class BusinessSettingsUpdate(BaseModel):
    workflow_invoicing: Optional[InvoicingWorkflow] = None
    workflow_quoting: Optional[QuotingWorkflow] = None
    workflow_payment_timing: Optional[PaymentTiming] = None
    workflow_tax_inclusive: Optional[bool] = None
    workflow_include_payment_terms: Optional[bool] = None
    workflow_enable_reminders: Optional[bool] = None
    workflow_show_whatsapp_button: Optional[bool] = None
    workflow_pipeline_quoted_stage: Optional[bool] = None
    workflow_job_creation_default: Optional[JobCreationDefault] = None
    workflow_distance_unit: Optional[str] = Field(None, max_length=10)
    workflow_auto_quote_followup: Optional[bool] = None
    workflow_quote_followup_delay_hrs: Optional[int] = None
    workflow_auto_review_requests: Optional[bool] = None
    workflow_review_request_delay_hrs: Optional[int] = None
    workflow_review_link: Optional[AnyHttpUrl] = None
    payment_link: Optional[AnyHttpUrl] = None
    default_city: Optional[str] = Field(None, max_length=100)
    default_country: Optional[str] = Field(None, max_length=100)
    default_tax_rate: Optional[float] = None
    marketing_settings: Optional[Dict[str, Any]] = None

class WageConfigurationUpdate(BaseModel):
    model_type: Optional[WageModelType] = None
    rate_value: Optional[float] = None
    tax_withholding_rate: Optional[float] = None
    allow_expense_claims: Optional[bool] = None

# --- Search ---

class SearchResult(BaseModel):
    type: str = Field(..., max_length=50) # customer, job, request
    id: int
    title: str = Field(..., max_length=200)
    subtitle: Optional[str] = Field(None, max_length=200)
    metadata: Optional[Dict[str, Any]] = None

class GlobalSearchResponse(BaseModel):
    query: str = Field(..., max_length=200)
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
    employee_name: str = Field(..., max_length=100)
    steps: List[RoutingStep]

class RoutingMetrics(BaseModel):
    total_distance: float # meters
    total_duration: float # seconds
    jobs_assigned: int
    unassigned_count: int

class RoutingResponse(BaseModel):
    date: str = Field(..., max_length=10)
    metrics: RoutingMetrics
    routes: List[RouteSchema]
    unassigned_jobs: List[JobSchema]

class GeocodeResponse(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    street: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    full_address: Optional[str] = Field(None, max_length=500)

class AddressSearchType(str, Enum):
    CUSTOMER = "customer"
    JOB = "job"

class AddressSearchResult(BaseModel):
    id: int
    address: str = Field(..., max_length=255)
    customer: Optional[str] = Field(None, max_length=200)
    type: AddressSearchType


# --- Data Management ---

class ImportJobSchema(BaseModel):
    id: int
    filename: Optional[str] = Field(None, max_length=255)
    record_count: int
    status: SyncLogStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ExportRequestSchema(BaseModel):
    id: int
    query: str = Field(..., max_length=500)
    format: ExportFormat
    status: ExportStatus
    public_url: Optional[str] = Field(None, max_length=500)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DataActivitySchema(BaseModel):
    imports: List[ImportJobSchema]
    exports: List[ExportRequestSchema]

class ExportCreateRequest(BaseModel):
    query: Optional[str] = Field(None, max_length=500)
    format: ExportFormat # 'CSV', 'Excel', 'JSON'

# --- Marketing Schemas ---

class CampaignSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)
    channel: CampaignChannel
    status: CampaignStatus
    total_recipients: int
    sent_count: int
    failed_count: int
    created_at: datetime
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CampaignCreate(BaseModel):
    name: str = Field(..., max_length=100)
    channel: CampaignChannel
    body: str = Field(..., max_length=5000)
    subject: Optional[str] = Field(None, max_length=200)
    recipient_query: str = Field("all", max_length=500)


class WhatsAppTemplateSchema(BaseModel):
    id: int
    name: str = Field(..., max_length=100)
    language: str = Field(..., max_length=10)
    category: WhatsAppTemplateCategory
    status: WhatsAppTemplateStatus
    components: List[Dict[str, Any]]
    meta_template_id: Optional[str] = Field(None, max_length=100)
    rejection_reason: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class WhatsAppTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    category: WhatsAppTemplateCategory
    components: List[Dict[str, Any]]
    language: str = Field("en_US", max_length=10)
