from datetime import datetime, timezone
from typing import List, Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
import enum
from src.database import Base


class UserRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class ConversationStatus(str, enum.Enum):
    IDLE = "idle"
    WAITING_CONFIRM = "waiting_confirm"
    SETTINGS = "settings"


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="business")
    customers: Mapped[List["Customer"]] = relationship(back_populates="business")
    jobs: Mapped[List["Job"]] = relationship(back_populates="business")
    requests: Mapped[List["Request"]] = relationship(back_populates="business")
    services: Mapped[List["Service"]] = relationship(back_populates="business")


class User(Base):
    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(String, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    preferences: Mapped[dict] = mapped_column(
        JSON, default=lambda: {"confirm_by_default": False}
    )
    timezone: Mapped[str] = mapped_column(String, default="UTC")

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="users")


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
    original_address_input: Mapped[Optional[str]] = mapped_column(String)
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
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
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="jobs")
    customer: Mapped["Customer"] = relationship(back_populates="jobs")
    line_items: Mapped[List["LineItem"]] = relationship(back_populates="job", cascade="all, delete-orphan")

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

    phone_number: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[ConversationStatus] = mapped_column(
        SAEnum(ConversationStatus), default=ConversationStatus.IDLE
    )
    draft_data: Mapped[Optional[Any]] = mapped_column(JSON)
    last_action_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
