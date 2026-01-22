from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Float, Enum as SAEnum, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import enum
from src.database import Base
from src.models.integration_config import IntegrationConfig, IntegrationType


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class ConversationStatus(str, enum.Enum):
    IDLE = "idle"
    WAITING_CONFIRM = "waiting_confirm"
    PENDING_AUTO_CONFIRM = "pending_auto_confirm"
    SETTINGS = "settings"
    DATA_MANAGEMENT = "data_management"
    BILLING = "billing"
    EMPLOYEE_MANAGEMENT = "employee_management"


class PipelineStage(str, enum.Enum):
    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    CONVERTED_ONCE = "converted_once"
    CONVERTED_RECURRENT = "converted_recurrent"
    NOT_INTERESTED = "not_interested"
    LOST = "lost"


class QuoteStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class QuickBooksSyncStatus(str, enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    SKIPPED = "skipped"


class SyncType(str, enum.Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


class SyncLogStatus(str, enum.Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class InvoicingWorkflow(str, enum.Enum):
    NEVER = "never"
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class QuotingWorkflow(str, enum.Enum):
    NEVER = "never"
    MANUAL = "manual"
    AUTOMATIC = "automatic"


class PaymentTiming(str, enum.Enum):
    ALWAYS_PAID_ON_SPOT = "always_paid_on_spot"
    USUALLY_PAID_ON_SPOT = "usually_paid_on_spot"
    PAID_LATER = "paid_later"


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
    subscription_status: Mapped[str] = mapped_column(String, default="free")
    seat_limit: Mapped[int] = mapped_column(Integer, default=1)
    active_addons: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["manage_employees", "campaigns"])
    
    # QuickBooks connection metadata (non-sensitive)
    quickbooks_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    quickbooks_last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Workflow Settings
    workflow_invoicing: Mapped[Optional[InvoicingWorkflow]] = mapped_column(SAEnum(InvoicingWorkflow), nullable=True)
    workflow_quoting: Mapped[Optional[QuotingWorkflow]] = mapped_column(SAEnum(QuotingWorkflow), nullable=True)
    workflow_payment_timing: Mapped[Optional[PaymentTiming]] = mapped_column(SAEnum(PaymentTiming), nullable=True)
    workflow_tax_inclusive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    workflow_include_payment_terms: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    workflow_enable_reminders: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # T020 - Usage-Based Billing
    message_count_current_period: Mapped[int] = mapped_column(Integer, default=0)
    billing_cycle_anchor: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="business")
    customers: Mapped[List["Customer"]] = relationship(back_populates="business")
    jobs: Mapped[List["Job"]] = relationship(back_populates="business")
    requests: Mapped[List["Request"]] = relationship(back_populates="business")
    services: Mapped[List["Service"]] = relationship(back_populates="business")
    import_jobs: Mapped[List["ImportJob"]] = relationship(back_populates="business")
    export_requests: Mapped[List["ExportRequest"]] = relationship(back_populates="business")
    quotes: Mapped[List["Quote"]] = relationship(back_populates="business")
    sync_logs: Mapped[List["SyncLog"]] = relationship(back_populates="business")
    invitations: Mapped[List["Invitation"]] = relationship(back_populates="business")



class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.EMPLOYEE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    preferred_channel: Mapped[str] = mapped_column(String, default="whatsapp")
    preferences: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"confirm_by_default": False}
    )
    timezone: Mapped[str] = mapped_column(String, default="UTC")
    default_start_location_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    default_start_location_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Location tracking fields
    current_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="users")
    conversation_state: Mapped[Optional["ConversationState"]] = relationship(back_populates="user")
    messages: Mapped[List["Message"]] = relationship(back_populates="user")


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
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(SAEnum(QuickBooksSyncStatus), nullable=True, default=QuickBooksSyncStatus.PENDING)
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @validates("default_price")
    def validate_price(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"Service price cannot be negative: {value}")
        return value


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    service_id: Mapped[Optional[int]] = mapped_column(ForeignKey("services.id"), nullable=True)
    description: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float)
    total_price: Mapped[float] = mapped_column(Float)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="line_items")
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
    name: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String)
    details: Mapped[Optional[str]] = mapped_column(Text)
    street: Mapped[Optional[str]] = mapped_column(String)
    city: Mapped[Optional[str]] = mapped_column(String)
    country: Mapped[Optional[str]] = mapped_column(String)
    postal_code: Mapped[Optional[str]] = mapped_column(String)
    original_address_input: Mapped[Optional[str]] = mapped_column(String)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    pipeline_stage: Mapped[PipelineStage] = mapped_column(
        SAEnum(PipelineStage), default=PipelineStage.NOT_CONTACTED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="customers")
    jobs: Mapped[List["Job"]] = relationship(back_populates="customer")
    quotes: Mapped[List["Quote"]] = relationship(back_populates="customer")
    availability: Mapped[List["CustomerAvailability"]] = relationship(back_populates="customer", cascade="all, delete-orphan")
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(SAEnum(QuickBooksSyncStatus), nullable=True, default=QuickBooksSyncStatus.PENDING)
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
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    value: Mapped[Optional[float]] = mapped_column(Float)
    location: Mapped[Optional[str]] = mapped_column(String)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    postal_code: Mapped[Optional[str]] = mapped_column(String)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    estimated_duration: Mapped[int] = mapped_column(Integer, default=60)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="jobs")
    customer: Mapped["Customer"] = relationship(back_populates="jobs")
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    employee: Mapped[Optional["User"]] = relationship(foreign_keys=[employee_id])
    line_items: Mapped[List["LineItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    invoices: Mapped[List["Invoice"]] = relationship(back_populates="job", cascade="all, delete-orphan")

    @validates("value")
    def validate_value(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"Job value cannot be negative: {value}")
        return value


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="requests")


class ConversationState(Base):
    __tablename__ = "conversation_states"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    state: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus), default=ConversationStatus.IDLE
    )
    draft_data: Mapped[Optional[Any]] = mapped_column(JSON)
    last_action_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    pending_action_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime)
    pending_action_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    active_channel: Mapped[str] = mapped_column(String, default="whatsapp")
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
    status: Mapped[str] = mapped_column(String, default="SENT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="invoices")
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(SAEnum(QuickBooksSyncStatus), nullable=True, default=QuickBooksSyncStatus.PENDING)
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    from_number: Mapped[str] = mapped_column(String, index=True)
    to_number: Mapped[Optional[str]] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole))
    channel_type: Mapped[str] = mapped_column(String, default="whatsapp")
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    log_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship()
    user: Mapped[Optional["User"]] = relationship(back_populates="messages")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    status: Mapped[str] = mapped_column(String, default="pending")  # 'pending', 'processing', 'completed', 'failed'
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
    status: Mapped[QuoteStatus] = mapped_column(SAEnum(QuoteStatus), default=QuoteStatus.DRAFT)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    external_token: Mapped[str] = mapped_column(String, unique=True, index=True)
    blob_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("jobs.id"), nullable=True)
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
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(SAEnum(QuickBooksSyncStatus), nullable=True, default=QuickBooksSyncStatus.PENDING)
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class QuoteLineItem(Base):
    __tablename__ = "quote_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"), index=True)
    service_id: Mapped[Optional[int]] = mapped_column(ForeignKey("services.id"), nullable=True)
    description: Mapped[str] = mapped_column(String)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float)
    total: Mapped[float] = mapped_column(Float)

    # Relationships
    quote: Mapped["Quote"] = relationship(back_populates="items")


class ExportRequest(Base):
    __tablename__ = "export_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    status: Mapped[str] = mapped_column(String, default="pending")  # 'pending', 'processing', 'completed', 'failed'
    query: Mapped[str] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String)  # 'csv', 'excel', 'json'
    s3_key: Mapped[Optional[str]] = mapped_column(String)
    public_url: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="export_requests")



class MessageType(str, enum.Enum):
    WHATSAPP = "whatsapp"
    SMS = "sms"


class MessageStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class MessageLog(Base):
    __tablename__ = "message_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[Optional[int]] = mapped_column(ForeignKey("businesses.id"), index=True)
    recipient_phone: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[MessageType] = mapped_column(SAEnum(MessageType))
    status: Mapped[MessageStatus] = mapped_column(
        SAEnum(MessageStatus), default=MessageStatus.PENDING
    )
    trigger_source: Mapped[str] = mapped_column(String)
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
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
    payment_method: Mapped[str] = mapped_column(String)  # 'cash', 'card', 'bank_transfer', etc.
    status: Mapped[str] = mapped_column(String, default="completed")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship()
    
    # QuickBooks sync tracking
    quickbooks_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    quickbooks_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    quickbooks_sync_status: Mapped[Optional[QuickBooksSyncStatus]] = mapped_column(SAEnum(QuickBooksSyncStatus), nullable=True, default=QuickBooksSyncStatus.PENDING)
    quickbooks_sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    
    # Sync metadata
    sync_timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )
    sync_type: Mapped[SyncType] = mapped_column(
        SAEnum(SyncType),
        nullable=False
    )
    
    # Results
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_succeeded: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    # Status and errors
    status: Mapped[SyncLogStatus] = mapped_column(
        SAEnum(SyncLogStatus),
        nullable=False
    )
    error_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Duration tracking
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    business: Mapped["Business"] = relationship(back_populates="sync_logs")


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    inviter_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invitee_identifier: Mapped[str] = mapped_column(String, index=True)  # phone or email
    token: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        SAEnum(InvitationStatus), default=InvitationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="invitations")
    inviter: Mapped["User"] = relationship()

