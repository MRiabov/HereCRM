from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Text,
    JSON,
    Float,
    Enum as SAEnum,
    Integer,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import enum
from src.database import Base
from src.models.integration_config import IntegrationConfig, IntegrationType
from src.models.document import Document, DocumentType
from src.models.campaign import (
    Campaign,
    CampaignRecipient,
    CampaignStatus,
    CampaignChannel,
    RecipientStatus,
)
from src.models.whatsapp_template import (
    WhatsAppTemplate,
    WhatsAppTemplateStatus,
    WhatsAppTemplateCategory,
)


from src.models.base_enum import RobustEnum, SafeSAEnum


class UserRole(RobustEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class ConversationStatus(RobustEnum):
    IDLE = "IDLE"
    ONBOARDING = "ONBOARDING"
    WAITING_CONFIRM = "WAITING_CONFIRM"
    PENDING_AUTO_CONFIRM = "PENDING_AUTO_CONFIRM"
    SETTINGS = "SETTINGS"
    DATA_MANAGEMENT = "DATA_MANAGEMENT"
    BILLING = "BILLING"
    EMPLOYEE_MANAGEMENT = "EMPLOYEE_MANAGEMENT"


class PipelineStage(RobustEnum):
    NEW_LEAD = "NEW_LEAD"
    NOT_CONTACTED = "NOT_CONTACTED"
    CONTACTED = "CONTACTED"
    QUOTED = "QUOTED"
    CONVERTED_ONCE = "CONVERTED_ONCE"
    CONVERTED_RECURRENT = "CONVERTED_RECURRENT"
    NOT_INTERESTED = "NOT_INTERESTED"
    LOST = "LOST"


class LeadSource(RobustEnum):
    API = "api"
    WEBHOOK = "webhook"
    WHATSAPP = "whatsapp"
    SMS = "sms"
    PWA = "pwa"
    FB_ADS = "fb_ads"
    MANUAL = "manual"
    GENERIC = "generic"
    ZAPIER = "zapier"
    CRON = "cron"


class InvoiceStatus(RobustEnum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Urgency(RobustEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ExportStatus(RobustEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ExportFormat(RobustEnum):
    CSV = "csv"
    EXCEL = "excel"
    ZIP = "zip"
    JSON = "json"


class PaymentStatus(RobustEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class QuoteStatus(RobustEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RequestStatus(RobustEnum):
    PENDING = "PENDING"
    CONVERTED = "CONVERTED"
    DISMISSED = "DISMISSED"
    COMPLETED = "COMPLETED"
    LOGGED = "LOGGED"


class QuickBooksSyncStatus(RobustEnum):
    PENDING = "PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class SyncType(RobustEnum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"


class SyncLogStatus(RobustEnum):
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class InvoicingWorkflow(RobustEnum):
    NEVER = "NEVER"
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class QuotingWorkflow(RobustEnum):
    NEVER = "NEVER"
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class PaymentTiming(RobustEnum):
    ALWAYS_PAID_ON_SPOT = "ALWAYS_PAID_ON_SPOT"
    USUALLY_PAID_ON_SPOT = "USUALLY_PAID_ON_SPOT"
    PAID_LATER = "PAID_LATER"


class JobCreationDefault(RobustEnum):
    MARK_DONE = "MARK_DONE"
    UNSCHEDULED = "UNSCHEDULED"
    AUTO_SCHEDULE = "AUTO_SCHEDULE"
    SCHEDULED_TODAY = "SCHEDULED_TODAY"


class DistanceUnit(RobustEnum):
    MILES = "mi"
    KILOMETERS = "km"


class OnboardingChoiceType(RobustEnum):
    CREATE = "create"
    JOIN = "join"


class SubscriptionStatus(RobustEnum):
    FREE = "free"
    PRO = "pro"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"


class PaymentMethod(RobustEnum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class MessageType(RobustEnum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    EMAIL = "EMAIL"
    PWA_CHAT = "PWA_CHAT"
    GENERIC = "GENERIC"


class MessageStatus(RobustEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DRAFT = "DRAFT"


class WageModelType(RobustEnum):
    COMMISSION = "COMMISSION"
    HOURLY_PER_JOB = "HOURLY_PER_JOB"
    HOURLY_PER_SHIFT = "HOURLY_PER_SHIFT"
    FIXED_DAILY = "FIXED_DAILY"


class LedgerEntryType(RobustEnum):
    WAGE = "WAGE"
    PAYOUT = "PAYOUT"
    EXPENSE_REIMBURSEMENT = "EXPENSE_REIMBURSEMENT"


class PromotionAction(RobustEnum):
    SCHEDULE = "SCHEDULE"
    COMPLETE = "COMPLETE"
    LOG = "LOG"
    QUOTE = "QUOTE"


class MessageTriggerSource(RobustEnum):
    MANUAL = "MANUAL"
    BOT_REPLY = "BOT_REPLY"
    SYSTEM_NOTIFICATION = "SYSTEM_NOTIFICATION"
    INVITATION_FLOW = "INVITATION_FLOW"
    QUOTE_SENT = "QUOTE_SENT"
    QUOTE_FOLLOWUP = "QUOTE_FOLLOWUP"
    REVIEW_REQUEST = "REVIEW_REQUEST"
    SCHEDULER = "SCHEDULER"
    EVENT = "EVENT"
    JOB_BOOKED = "JOB_BOOKED"
    JOB_SCHEDULED = "JOB_SCHEDULED"
    ON_MY_WAY = "ON_MY_WAY"
    AUTOROUTE_ASSIGNMENT = "AUTOROUTE_ASSIGNMENT"
    API = "API"
    PWA_CHAT_MANUAL = "PWA_CHAT_MANUAL"
    CAMPAIGN = "CAMPAIGN"
    STATUS_CHANGE = "STATUS_CHANGE"
    INVITATION = "INVITATION"


class TriggerSource(RobustEnum):
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class EntityType(RobustEnum):
    JOB = "JOB"
    REQUEST = "REQUEST"
    EXPENSE = "EXPENSE"
    LEDGER = "LEDGER"
    CUSTOMER = "CUSTOMER"
    LEAD = "LEAD"
    QUOTE = "QUOTE"
    INVOICE = "INVOICE"
    ALL = "ALL"


class JobStatus(RobustEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    BOOKED = "BOOKED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    payment_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Billing Fields (Shimmed from WP00)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        SafeSAEnum(SubscriptionStatus), default=SubscriptionStatus.FREE
    )
    seat_limit: Mapped[int] = mapped_column(Integer, default=1)
    active_addons: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["manage_employees", "campaigns"]
    )

    # QuickBooks connection metadata (non-sensitive)
    quickbooks_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    quickbooks_last_sync: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    clerk_org_id: Mapped[Optional[str]] = mapped_column(
        String, unique=True, nullable=True
    )

    # Workflow Settings
    workflow_invoicing: Mapped[Optional[InvoicingWorkflow]] = mapped_column(
        SafeSAEnum(InvoicingWorkflow), nullable=True
    )
    workflow_quoting: Mapped[Optional[QuotingWorkflow]] = mapped_column(
        SafeSAEnum(QuotingWorkflow), nullable=True
    )
    workflow_payment_timing: Mapped[Optional[PaymentTiming]] = mapped_column(
        SafeSAEnum(PaymentTiming), nullable=True
    )
    workflow_tax_inclusive: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    workflow_include_payment_terms: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    workflow_enable_reminders: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True
    )
    workflow_show_whatsapp_button: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, default=False
    )
    workflow_pipeline_quoted_stage: Mapped[bool] = mapped_column(Boolean, default=True)
    workflow_job_creation_default: Mapped[Optional[JobCreationDefault]] = mapped_column(
        SafeSAEnum(JobCreationDefault), nullable=True
    )
    workflow_distance_unit: Mapped[DistanceUnit] = mapped_column(
        SafeSAEnum(DistanceUnit), default=DistanceUnit.MILES
    )

    # Automatic Messaging Settings (Feature 003)
    workflow_auto_quote_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow_quote_followup_delay_hrs: Mapped[int] = mapped_column(Integer, default=48)
    workflow_auto_review_requests: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow_review_request_delay_hrs: Mapped[int] = mapped_column(Integer, default=2)
    workflow_review_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Automatic Messaging Templates & Triggers
    marketing_settings: Mapped[dict] = mapped_column(JSON, default={})
    messenger_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default={})

    default_city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_country: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    default_tax_rate: Mapped[float] = mapped_column(Float, default=0.0)

    invite_code: Mapped[Optional[str]] = mapped_column(
        String(20), unique=True, nullable=True, index=True
    )

    # T020 - Usage-Based Billing
    message_count_current_period: Mapped[int] = mapped_column(Integer, default=0)
    billing_cycle_anchor: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    message_credits: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="business")
    customers: Mapped[List["Customer"]] = relationship(back_populates="business")
    jobs: Mapped[List["Job"]] = relationship(back_populates="business")
    requests: Mapped[List["Request"]] = relationship(back_populates="business")
    services: Mapped[List["Service"]] = relationship(back_populates="business")
    import_jobs: Mapped[List["ImportJob"]] = relationship(back_populates="business")
    export_requests: Mapped[List["ExportRequest"]] = relationship(
        back_populates="business"
    )
    quotes: Mapped[List["Quote"]] = relationship(back_populates="business")
    sync_logs: Mapped[List["SyncLog"]] = relationship(back_populates="business")
    invitations: Mapped[List["Invitation"]] = relationship(back_populates="business")
    campaigns: Mapped[List["Campaign"]] = relationship(back_populates="business")
    whatsapp_templates: Mapped[List["WhatsAppTemplate"]] = relationship(
        back_populates="business"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(
        String, unique=True, nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    role: Mapped[UserRole] = mapped_column(
        SafeSAEnum(UserRole), default=UserRole.EMPLOYEE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    preferred_channel: Mapped[MessageType] = mapped_column(
        SafeSAEnum(MessageType), default=MessageType.WHATSAPP
    )
    preferences: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"confirm_by_default": False}
    )
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    default_start_location_lat: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    default_start_location_lng: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Google Calendar Integration
    google_calendar_credentials: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )
    google_calendar_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    clerk_id: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)

    # Location tracking fields
    current_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Financial / Wage fields
    current_shift_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Usage tracking
    geocoding_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="users")
    conversation_state: Mapped[Optional["ConversationState"]] = relationship(
        back_populates="user", uselist=False
    )
    messages: Mapped[List["Message"]] = relationship(back_populates="user")
    wage_config: Mapped[Optional["WageConfiguration"]] = relationship(
        back_populates="user", uselist=False
    )
    ledger_entries: Mapped[List["LedgerEntry"]] = relationship(back_populates="user")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    default_price: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    estimated_duration: Mapped[int] = mapped_column(Integer, default=60)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="services")
    line_items: Mapped[List["LineItem"]] = relationship(back_populates="service")

    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(
        SafeSAEnum(QuickBooksSyncStatus),
        nullable=True,
        default=QuickBooksSyncStatus.PENDING,
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @validates("default_price")
    def validate_price(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"Service price cannot be negative: {value}")
        return value


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id"), nullable=True, index=True
    )
    service_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("services.id"), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)
    request_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("requests.id"), nullable=True, index=True
    )

    # Relationships
    job: Mapped[Optional["Job"]] = relationship(back_populates="line_items")
    request: Mapped[Optional["Request"]] = relationship(back_populates="line_items")
    service: Mapped[Optional["Service"]] = relationship(back_populates="line_items")

    @validates("quantity", "unit_price", "total_price")
    def validate_non_negative(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"{key.capitalize()} cannot be negative: {value}")
        return value


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String)
    email: Mapped[Optional[str]] = mapped_column(String, index=True)
    details: Mapped[Optional[str]] = mapped_column(Text)
    street: Mapped[Optional[str]] = mapped_column(String)
    city: Mapped[Optional[str]] = mapped_column(String)
    country: Mapped[Optional[str]] = mapped_column(String)
    postal_code: Mapped[Optional[str]] = mapped_column(String)
    original_address_input: Mapped[Optional[str]] = mapped_column(String)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    pipeline_stage: Mapped[PipelineStage] = mapped_column(
        SafeSAEnum(PipelineStage), default=PipelineStage.NOT_CONTACTED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Transient fields for API enrichment
    job_count: int = 0
    total_value: float = 0.0

    # Relationships

    business: Mapped["Business"] = relationship(back_populates="customers")
    jobs: Mapped[List["Job"]] = relationship(back_populates="customer")
    quotes: Mapped[List["Quote"]] = relationship(back_populates="customer")
    availability: Mapped[List["CustomerAvailability"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    documents: Mapped[List["Document"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )

    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(
        SafeSAEnum(QuickBooksSyncStatus),
        nullable=True,
        default=QuickBooksSyncStatus.PENDING,
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CustomerAvailability(Base):
    __tablename__ = "customer_availability"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="availability")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[JobStatus] = mapped_column(
        SafeSAEnum(JobStatus), default=JobStatus.PENDING
    )
    value: Mapped[Optional[float]] = mapped_column(Float)

    # Tax Information (Snapshot)
    subtotal: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[Optional[float]] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[Optional[float]] = mapped_column(Float, default=0.0)

    location: Mapped[Optional[str]] = mapped_column(String)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    postal_code: Mapped[Optional[str]] = mapped_column(String)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)

    # Google Calendar Integration
    gcal_event_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    estimated_duration: Mapped[int] = mapped_column(Integer, default=60)
    begun_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_actual_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="jobs")
    customer: Mapped["Customer"] = relationship(back_populates="jobs")
    employee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    employee: Mapped[Optional["User"]] = relationship(foreign_keys=[employee_id])
    line_items: Mapped[List["LineItem"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    invoices: Mapped[List["Invoice"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    expenses: Mapped[List["Expense"]] = relationship(back_populates="job")

    @validates("value")
    def validate_value(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"Job value cannot be negative: {value}")
        return value


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )

    # Original field renamed or mapped to description?
    # Frontend uses 'description', Request model had 'content'. I will use 'description' for consistency.
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[RequestStatus] = mapped_column(
        SafeSAEnum(RequestStatus), default=RequestStatus.PENDING
    )
    urgency: Mapped[Urgency] = mapped_column(
        SafeSAEnum(Urgency), default=Urgency.MEDIUM
    )
    expected_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Tax Information
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)

    follow_up_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # For leads where we haven't created a customer record yet
    customer_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="requests")
    customer: Mapped[Optional["Customer"]] = relationship()
    line_items: Mapped[List["LineItem"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class ConversationState(Base):
    __tablename__ = "conversation_states"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    state: Mapped[ConversationStatus] = mapped_column(
        SafeSAEnum(ConversationStatus), default=ConversationStatus.IDLE
    )
    draft_data: Mapped[Optional[Any]] = mapped_column(JSON)
    last_action_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    pending_action_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime)
    pending_action_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    active_channel: Mapped[MessageType] = mapped_column(
        SafeSAEnum(MessageType), default=MessageType.WHATSAPP
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversation_state")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    s3_key: Mapped[str] = mapped_column(String)
    public_url: Mapped[str] = mapped_column(String)
    payment_link: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        SafeSAEnum(InvoiceStatus), default=InvoiceStatus.SENT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="invoices")

    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(
        SafeSAEnum(QuickBooksSyncStatus),
        nullable=True,
        default=QuickBooksSyncStatus.PENDING,
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MessageRole(RobustEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    from_number: Mapped[str] = mapped_column(String, index=True)
    to_number: Mapped[Optional[str]] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    role: Mapped[MessageRole] = mapped_column(SafeSAEnum(MessageRole))
    channel_type: Mapped[MessageType] = mapped_column(
        SafeSAEnum(MessageType), default=MessageType.WHATSAPP
    )
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    log_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship()
    user: Mapped[Optional["User"]] = relationship(back_populates="messages")


class ImportStatus(RobustEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    status: Mapped[ImportStatus] = mapped_column(
        SafeSAEnum(ImportStatus), default=ImportStatus.PENDING
    )
    file_url: Mapped[str] = mapped_column(String)
    filename: Mapped[Optional[str]] = mapped_column(String)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="import_jobs")


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    status: Mapped[QuoteStatus] = mapped_column(
        SafeSAEnum(QuoteStatus), default=QuoteStatus.DRAFT
    )
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)

    # Tax Information
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)

    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    external_token: Mapped[str] = mapped_column(String, unique=True, index=True)
    blob_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # bolt-opt: index=True for faster lookups by job_id
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="quotes")
    business: Mapped["Business"] = relationship(back_populates="quotes")
    items: Mapped[List["QuoteLineItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan"
    )
    job: Mapped[Optional["Job"]] = relationship()

    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(
        SafeSAEnum(QuickBooksSyncStatus),
        nullable=True,
        default=QuickBooksSyncStatus.PENDING,
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    service_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("services.id"), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float)

    # Relationships
    quote: Mapped["Quote"] = relationship(back_populates="items")


class ExportRequest(Base):
    __tablename__ = "export_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    status: Mapped[ExportStatus] = mapped_column(
        SafeSAEnum(ExportStatus), default=ExportStatus.PENDING
    )
    query: Mapped[str] = mapped_column(Text)
    format: Mapped[ExportFormat] = mapped_column(
        SafeSAEnum(ExportFormat), default=ExportFormat.CSV
    )
    s3_key: Mapped[Optional[str]] = mapped_column(String)
    public_url: Mapped[Optional[str]] = mapped_column(String)
    error_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="export_requests")


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("businesses.id"), index=True
    )
    recipient_phone: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[MessageType] = mapped_column(SafeSAEnum(MessageType))
    status: Mapped[MessageStatus] = mapped_column(
        SafeSAEnum(MessageStatus), default=MessageStatus.PENDING
    )
    trigger_source: Mapped[MessageTriggerSource] = mapped_column(
        SafeSAEnum(MessageTriggerSource)
    )
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    log_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    payment_date: Mapped[datetime] = mapped_column(DateTime)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SafeSAEnum(PaymentMethod), default=PaymentMethod.CASH
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SafeSAEnum(PaymentStatus), default=PaymentStatus.COMPLETED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship()

    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(
        SafeSAEnum(QuickBooksSyncStatus),
        nullable=True,
        default=QuickBooksSyncStatus.PENDING,
    )
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)

    # Sync metadata
    sync_timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    sync_type: Mapped[SyncType] = mapped_column(SafeSAEnum(SyncType), nullable=False)

    # Results
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Status and errors
    status: Mapped[SyncLogStatus] = mapped_column(
        SafeSAEnum(SyncLogStatus), nullable=False
    )
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Duration tracking
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="sync_logs")


class InvitationStatus(RobustEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    invitee_identifier: Mapped[str] = mapped_column(
        String, index=True
    )  # phone or email
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        SafeSAEnum(InvitationStatus), default=InvitationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="invitations")
    inviter: Mapped["User"] = relationship()


class WageConfiguration(Base):
    __tablename__ = "wage_configurations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    model_type: Mapped[WageModelType] = mapped_column(SafeSAEnum(WageModelType))
    rate_value: Mapped[float] = mapped_column(Float)
    tax_withholding_rate: Mapped[float] = mapped_column(Float, default=0.0)
    allow_expense_claims: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="wage_config")


class ExpenseCategory(RobustEnum):
    FUEL = "FUEL"
    TOOLS = "TOOLS"
    MATERIAL = "MATERIAL"
    TRAVEL = "TRAVEL"
    GENERAL = "GENERAL"
    OTHER = "OTHER"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id"), nullable=True, index=True
    )
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[ExpenseCategory] = mapped_column(
        SafeSAEnum(ExpenseCategory), default=ExpenseCategory.OTHER
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    receipt_url: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship()
    job: Mapped[Optional["Job"]] = relationship(back_populates="expenses")
    employee: Mapped["User"] = relationship()


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    entry_type: Mapped[LedgerEntryType] = mapped_column(SafeSAEnum(LedgerEntryType))
    description: Mapped[str] = mapped_column(String)
    job_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("jobs.id"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship()
    user: Mapped["User"] = relationship(back_populates="ledger_entries")
    job: Mapped[Optional["Job"]] = relationship()
