from src.models import Urgency
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field, AnyHttpUrl
from src.models import (
    JobStatus, PipelineStage, InvoicingWorkflow, QuotingWorkflow, 
    PaymentTiming, JobCreationDefault, WageModelType, QuoteStatus, SyncLogStatus,
    CampaignStatus, CampaignChannel, WhatsAppTemplateStatus, WhatsAppTemplateCategory,
    InvoiceStatus, ExportStatus, ExportFormat, RequestStatus, UserRole, MessageRole,
    ExpenseCategory, LedgerEntryType, EntityType, DistanceUnit, OnboardingChoiceType
)
from enum import Enum

# --- Constants ---
PHONE_PATTERN = r"(^\+?\d{1,15}$|^$)"
EMAIL_PATTERN = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$|^$)"

# --- Shared / Base Schemas ---

class WageConfigurationSchema(BaseModel):
    model_type: WageModelType
    rate_value: float = Field(..., ge=0)
    tax_withholding_rate: float = Field(..., ge=0, le=1)
    allow_expense_claims: bool

    model_config = ConfigDict(from_attributes=True)

class UserSchema(BaseModel):
    id: int = Field(..., ge=1)
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
    id: int = Field(..., ge=1)
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
    job_count: int = Field(0, ge=0)
    total_value: float = Field(0.0, ge=0)

    model_config = ConfigDict(from_attributes=True)


class LineItemSchema(BaseModel):
    id: int = Field(..., ge=1)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    total_price: float = Field(..., ge=0)
    service_id: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(from_attributes=True)

class LineItemCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(1.0, ge=0)
    unit_price: float = Field(..., ge=0)
    service_id: Optional[int] = Field(None, ge=1)

class JobSchema(BaseModel):
    id: int = Field(..., ge=1)
    description: Optional[str] = Field(None, max_length=1000)
    status: JobStatus
    scheduled_at: Optional[datetime]
    value: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=255)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    paid: bool = False
    estimated_duration: int = Field(60, ge=0)
    begun_at: Optional[datetime] = None
    total_actual_duration_seconds: int = Field(0, ge=0)
    customer: Optional[CustomerSchema]
    employee: Optional[UserSchema] = None
    line_items: List[LineItemSchema] = []

    model_config = ConfigDict(from_attributes=True)
    

class OnboardingChoice(BaseModel):
    choice: OnboardingChoiceType
    invite_code: Optional[str] = Field(None, min_length=1, max_length=50)
    business_name: Optional[str] = Field(None, min_length=1, max_length=100)

# --- Dashboard Schemas ---

class DashboardStats(BaseModel):
    revenue_monthly: float = Field(..., ge=0)
    active_leads_count: int = Field(..., ge=0)
    leads_need_followup: int = Field(..., ge=0)
    pipeline_breakdown: Dict[str, int] = Field(..., description="Map of pipeline stage to count")

class ActivityType(str, Enum):
    INVOICE = "invoice"
    JOB = "job"
    LEAD = "lead"

class RecentActivity(BaseModel):
    type: ActivityType # 'invoice', 'lead', 'job'
    title: str = Field(..., max_length=200)
    description: str = Field(..., max_length=500)
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None # Keeping generic for activity as it varies widely

# --- Job Schemas ---

class JobListResponse(BaseModel):
    date: str = Field(..., max_length=20) # YYYY-MM-DD or "Unscheduled"
    jobs: List[JobSchema]

class JobCreate(BaseModel):
    customer_id: int = Field(..., ge=1)
    description: Optional[str] = Field(None, max_length=1000)
    status: JobStatus = JobStatus.PENDING
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=255)
    employee_id: Optional[int] = Field(None, ge=1)
    estimated_duration: Optional[int] = Field(None, ge=0) # Optional now, will be auto-calculated if items provided
    postal_code: Optional[str] = Field(None, max_length=20)
    items: Optional[List[LineItemCreate]] = None

class JobUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[JobStatus] = None
    scheduled_at: Optional[datetime] = None
    value: Optional[float] = Field(None, ge=0)
    employee_id: Optional[int] = Field(None, ge=1)
    estimated_duration: Optional[int] = Field(None, ge=0)
    location: Optional[str] = Field(None, max_length=255)
    postal_code: Optional[str] = Field(None, max_length=20)
    items: Optional[List[LineItemCreate]] = None

# --- Chat Schemas ---

class ChatMessageMetadataSchema(BaseModel):
    tool_name: Optional[str] = Field(None, max_length=100)
    arguments: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    tool: Optional[str] = Field(None, max_length=100)
    data: Optional[Dict[str, Any]] = None

class ChatMessage(BaseModel):
    id: Optional[int] = Field(None, ge=1)
    role: MessageRole
    content: str = Field(..., max_length=5000)
    timestamp: datetime
    is_outbound: bool
    is_executed: bool = False
    metadata: Optional[ChatMessageMetadataSchema] = None

class ChatMessageUpdate(BaseModel):
    message: str = Field(..., max_length=5000)

class ChatSendRequest(BaseModel):
    customer_id: int = Field(..., ge=0)
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
    id: int = Field(..., ge=1)
    job_id: int = Field(..., ge=1)
    total_amount: float = Field(..., ge=0)
    status: InvoiceStatus
    created_at: datetime
    public_url: str = Field(..., max_length=500)
    customer_name: Optional[str] = Field(None, max_length=200) # Enriched

    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):
    job_id: int = Field(..., ge=1)
    force_regenerate: bool = False
    invoice_number: Optional[str] = Field(None, max_length=50)
    status: InvoiceStatus
    issued_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = Field(None, max_length=1000)
    items: Optional[List[LineItemCreate]] = None

# --- Quote Schemas ---

class QuoteLineItemSchema(BaseModel):
    id: int = Field(..., ge=1)
    description: str = Field(..., min_length=1, max_length=500)
    quantity: float = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    service_id: Optional[int] = Field(None, ge=1)

    model_config = ConfigDict(from_attributes=True)

class QuoteSchema(BaseModel):
    id: int = Field(..., ge=1)
    customer_id: int = Field(..., ge=1)
    total_amount: float = Field(..., ge=0)
    status: QuoteStatus
    external_token: str = Field(..., min_length=1, max_length=100)
    public_url: Optional[str] = Field(None, max_length=500)
    created_at: datetime
    items: List[QuoteLineItemSchema] = []
    customer: Optional[CustomerSchema] = None

    model_config = ConfigDict(from_attributes=True)

class QuoteCreate(BaseModel):
    customer_id: int = Field(..., ge=1)
    title: Optional[str] = Field(None, max_length=200)
    location: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=1000)
    items: List[LineItemCreate]
    total_amount: Optional[float] = Field(None, ge=0)
    status: QuoteStatus = QuoteStatus.DRAFT

class CustomerDetailsSchema(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=PHONE_PATTERN)
    email: Optional[str] = Field(None, pattern=EMAIL_PATTERN)
    street: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)

# --- Request Schemas ---

class RequestSchema(BaseModel):
    id: int = Field(..., ge=1)
    description: str = Field(..., max_length=2000)
    status: RequestStatus
    urgency: Urgency
    expected_value: Optional[float] = Field(None, ge=0)
    subtotal: float = Field(0.0, ge=0)
    tax_amount: float = Field(0.0, ge=0)
    tax_rate: float = Field(0.0, ge=0)
    follow_up_date: Optional[datetime] = None
    customer_id: Optional[int] = Field(None, ge=1)
    customer_details: Optional[CustomerDetailsSchema] = None
    created_at: datetime
    customer: Optional[CustomerSchema] = None
    line_items: List[LineItemSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class RequestCreate(BaseModel):
    customer_id: Optional[int] = Field(None, ge=1)
    description: str = Field(..., min_length=1, max_length=2000)
    urgency: Urgency = Urgency.MEDIUM
    expected_value: Optional[float] = Field(None, ge=0)
    subtotal: Optional[float] = Field(0.0, ge=0)
    tax_amount: Optional[float] = Field(0.0, ge=0)
    tax_rate: Optional[float] = Field(0.0, ge=0)
    items: Optional[List[LineItemCreate]] = None
    follow_up_date: Optional[datetime] = None
    customer_details: Optional[CustomerDetailsSchema] = None

class RequestUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[RequestStatus] = None
    urgency: Optional[Urgency] = None
    expected_value: Optional[float] = Field(None, ge=0)
    subtotal: Optional[float] = Field(None, ge=0)
    tax_amount: Optional[float] = Field(None, ge=0)
    tax_rate: Optional[float] = Field(None, ge=0)
    items: Optional[List[LineItemCreate]] = None
    follow_up_date: Optional[datetime] = None
    customer_id: Optional[int] = Field(None, ge=1)

# --- Service Catalog Schemas ---

class ServiceSchema(BaseModel):
    id: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_price: float = Field(..., ge=0)
    estimated_duration: int = Field(..., ge=0)
    
    model_config = ConfigDict(from_attributes=True)

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_price: float = Field(..., ge=0)
    estimated_duration: int = Field(60, ge=0)

# --- Finance Schemas ---

class ExpenseSchema(BaseModel):
    id: int = Field(..., ge=1)
    description: Optional[str] = Field(None, max_length=500)
    category: ExpenseCategory
    amount: float
    created_at: datetime
    receipt_url: Optional[str] = Field(None, max_length=500)
    job_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

class ExpenseCreate(BaseModel):
    amount: float = Field(..., ge=0)
    category: ExpenseCategory
    description: Optional[str] = Field(None, max_length=500)
    job_id: Optional[int] = Field(None, ge=1)
    vendor: Optional[str] = Field(None, max_length=100)
    date: Optional[datetime] = None

class LedgerEntrySchema(BaseModel):
    id: int = Field(..., ge=1)
    employee_id: int = Field(..., ge=1)
    amount: float = Field(..., ge=0)
    type: LedgerEntryType
    description: str = Field(..., max_length=500)
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# --- Settings & Workflow ---

# --- Marketing & Automation ---

class MarketingTriggerSettingsSchema(BaseModel):
    jobBooked: bool = True
    onMyWay: bool = True
    jobCompleted: bool = False
    reviewRequest: bool = True
    quoteFollowup: bool = False

class MarketingTemplateSchema(BaseModel):
    name: str = Field(..., max_length=100)
    text: str = Field(..., max_length=5000)
    status: str = Field("DRAFT", pattern="^(DRAFT|PENDING|APPROVED|REJECTED)$")

class MarketingSettingsSchema(BaseModel):
    triggers: MarketingTriggerSettingsSchema = Field(default_factory=MarketingTriggerSettingsSchema)
    templates: Dict[str, MarketingTemplateSchema] = Field(default_factory=dict)

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
    workflow_distance_unit: Optional[DistanceUnit] = DistanceUnit.MILES
    workflow_auto_quote_followup: bool
    workflow_quote_followup_delay_hrs: int = Field(..., ge=0)
    workflow_auto_review_requests: bool
    workflow_review_request_delay_hrs: int = Field(..., ge=0)
    workflow_review_link: Optional[AnyHttpUrl] = None
    payment_link: Optional[AnyHttpUrl] = None
    default_city: Optional[str] = Field(None, max_length=100)
    default_country: Optional[str] = Field(None, max_length=100)
    default_tax_rate: Optional[float] = Field(0.0, ge=0)
    quickbooks_connected: bool
    quickbooks_last_sync: Optional[datetime] = None
    stripe_connected: bool
    seat_count: int = Field(..., ge=1)
    invite_code: Optional[str] = Field(None, max_length=50)
    billing_cycle_anchor: Optional[datetime] = None
    marketing_settings: Optional[MarketingSettingsSchema] = None

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
    workflow_distance_unit: Optional[DistanceUnit] = None
    workflow_auto_quote_followup: Optional[bool] = None
    workflow_quote_followup_delay_hrs: Optional[int] = None
    workflow_auto_review_requests: Optional[bool] = None
    workflow_review_request_delay_hrs: Optional[int] = None
    workflow_review_link: Optional[AnyHttpUrl] = None
    payment_link: Optional[AnyHttpUrl] = None
    default_city: Optional[str] = Field(None, max_length=100)
    default_country: Optional[str] = Field(None, max_length=100)
    default_tax_rate: Optional[float] = Field(None, ge=0)
    marketing_settings: Optional[MarketingSettingsSchema] = None

class WageConfigurationUpdate(BaseModel):
    model_type: Optional[WageModelType] = None
    rate_value: Optional[float] = None
    tax_withholding_rate: Optional[float] = None
    allow_expense_claims: Optional[bool] = None

# --- Search ---

class SearchResultMetadataSchema(BaseModel):
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    pipeline_stage: Optional[str] = Field(None, max_length=50)
    customer_name: Optional[str] = Field(None, max_length=100)
    scheduled_at: Optional[str] = Field(None, max_length=50)
    value: Optional[float] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=50)
    created_at: Optional[str] = Field(None, max_length=50)

class SearchResult(BaseModel):
    type: EntityType
    id: int = Field(..., ge=1)
    title: str = Field(..., min_length=1, max_length=200)
    subtitle: Optional[str] = Field(None, max_length=200)
    metadata: Optional[SearchResultMetadataSchema] = None

class GlobalSearchResponse(BaseModel):
    query: str = Field(..., max_length=200)
    results: List[SearchResult]

# --- Routing Schemas ---

class RoutingStep(BaseModel):
    job_id: int = Field(..., ge=1)
    arrival_time: Optional[datetime]
    departure_time: Optional[datetime]
    distance_to_next: Optional[float] = Field(None, ge=0)
    duration_to_next: Optional[float] = Field(None, ge=0)
    job: JobSchema

class RouteSchema(BaseModel):
    employee_id: int = Field(..., ge=1)
    employee_name: str = Field(..., max_length=100)
    steps: List[RoutingStep]

class RoutingMetrics(BaseModel):
    total_distance: float = Field(..., ge=0) # meters
    total_duration: float = Field(..., ge=0) # seconds
    jobs_assigned: int = Field(..., ge=0)
    unassigned_count: int = Field(..., ge=0)

class RoutingResponse(BaseModel):
    date: str = Field(..., max_length=20)
    metrics: RoutingMetrics
    routes: List[RouteSchema]
    unassigned_jobs: List[JobSchema]

class GeocodeResponse(BaseModel):
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    street: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    full_address: Optional[str] = Field(None, max_length=500)

class AddressSearchType(str, Enum):
    CUSTOMER = "customer"
    JOB = "job"

class AddressSearchResult(BaseModel):
    id: int = Field(..., ge=1)
    address: str = Field(..., min_length=1, max_length=255)
    customer: Optional[str] = Field(None, max_length=200)
    type: AddressSearchType


# --- Data Management ---

class ImportJobSchema(BaseModel):
    id: int = Field(..., ge=1)
    filename: Optional[str] = Field(None, max_length=255)
    record_count: int = Field(..., ge=0)
    status: SyncLogStatus
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ExportRequestSchema(BaseModel):
    id: int = Field(..., ge=1)
    query: str = Field(..., max_length=500)
    format: ExportFormat
    status: ExportStatus
    public_url: Optional[str] = Field(None, max_length=500)
    error_log: Optional[str] = Field(None, max_length=2000)
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
    id: int = Field(..., ge=1)
    name: str = Field(..., max_length=100)
    channel: CampaignChannel
    status: CampaignStatus
    total_recipients: int = Field(..., ge=0)
    sent_count: int = Field(0, ge=0)
    failed_count: int = Field(0, ge=0)
    created_at: datetime
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CampaignCreate(BaseModel):
    name: str = Field(..., max_length=100)
    channel: CampaignChannel
    body: str = Field(..., max_length=5000)
    subject: Optional[str] = Field(None, max_length=200)
    recipient_query: str = Field("all", min_length=1, max_length=500)


class WhatsAppButtonType(str, Enum):
    QUICK_REPLY = "QUICK_REPLY"
    PHONE_NUMBER = "PHONE_NUMBER"
    URL = "URL"
    COPY_CODE = "COPY_CODE"

class WhatsAppButtonSchema(BaseModel):
    type: WhatsAppButtonType
    text: Optional[str] = Field(None, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=20)
    url: Optional[str] = Field(None, max_length=2000)
    example: Optional[List[str]] = None

class WhatsAppTemplateComponentSchema(BaseModel):
    type: str = Field(..., pattern="^(HEADER|BODY|FOOTER|BUTTONS)$")
    format: Optional[str] = Field(None, pattern="^(TEXT|IMAGE|VIDEO|DOCUMENT)$")
    text: Optional[str] = Field(None, max_length=2000)
    example: Optional[Dict[str, Any]] = None
    buttons: Optional[List[WhatsAppButtonSchema]] = None

class WhatsAppTemplateSchema(BaseModel):
    id: int = Field(..., ge=1)
    name: str = Field(..., max_length=100)
    language: str = Field(..., pattern="^[a-z]{2}(_[A-Z]{2,4})?$", max_length=10)
    category: WhatsAppTemplateCategory
    status: WhatsAppTemplateStatus
    components: List[WhatsAppTemplateComponentSchema]
    meta_template_id: Optional[str] = Field(None, max_length=100)
    rejection_reason: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)

class WhatsAppTemplateCreate(BaseModel):
    name: str = Field(..., max_length=100)
    category: WhatsAppTemplateCategory
    components: List[WhatsAppTemplateComponentSchema]
    language: str = Field("en_US", max_length=10)
