from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Float, Enum as SAEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import enum
from src.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class ConversationStatus(str, enum.Enum):
    IDLE = "idle"
    WAITING_CONFIRM = "waiting_confirm"
    PENDING_AUTO_CONFIRM = "pending_auto_confirm"
    SETTINGS = "settings"
    DATA_MANAGEMENT = "data_management"


class PipelineStage(str, enum.Enum):
    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    CONVERTED_ONCE = "converted_once"
    CONVERTED_RECURRENT = "converted_recurrent"
    NOT_INTERESTED = "not_interested"
    LOST = "lost"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    
    # Billing Fields (Shimmed from WP00)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_status: Mapped[str] = mapped_column(String, default="free")
    seat_limit: Mapped[int] = mapped_column(Integer, default=1)
    active_addons: Mapped[List[str]] = mapped_column(JSON, default=lambda: ["manage_employees", "campaigns"])

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="business")
    customers: Mapped[List["Customer"]] = relationship(back_populates="business")
    jobs: Mapped[List["Job"]] = relationship(back_populates="business")
    requests: Mapped[List["Request"]] = relationship(back_populates="business")
    services: Mapped[List["Service"]] = relationship(back_populates="business")
    import_jobs: Mapped[List["ImportJob"]] = relationship(back_populates="business")
    export_requests: Mapped[List["ExportRequest"]] = relationship(back_populates="business")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    preferred_channel: Mapped[str] = mapped_column(String, default="whatsapp")
    preferences: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"confirm_by_default": False}
    )
    timezone: Mapped[str] = mapped_column(String, default="UTC")

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

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="services")
    line_items: Mapped[List["LineItem"]] = relationship(back_populates="service")

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
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="jobs")
    customer: Mapped["Customer"] = relationship(back_populates="jobs")
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
    status: Mapped[str] = mapped_column(String, default="SENT")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="invoices")


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

