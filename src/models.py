from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from src.database import Base

class UserRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"

class ConversationStatus(str, enum.Enum):
    IDLE = "idle"
    WAITING_CONFIRM = "waiting_confirm"

class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="business")
    customers: Mapped[List["Customer"]] = relationship(back_populates="business")
    jobs: Mapped[List["Job"]] = relationship(back_populates="business")
    requests: Mapped[List["Request"]] = relationship(back_populates="business")

class User(Base):
    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(String, primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    preferences: Mapped[dict] = mapped_column(JSON, default=lambda: {"confirm_by_default": False})

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="users")

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String)
    details: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="customers")
    jobs: Mapped[List["Job"]] = relationship(back_populates="customer")

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")
    value: Mapped[Optional[float]] = mapped_column(Float)
    location: Mapped[Optional[str]] = mapped_column(String)
    
    # Relationships
    business: Mapped["Business"] = relationship(back_populates="jobs")
    customer: Mapped["Customer"] = relationship(back_populates="jobs")

class Request(Base):
    __tablename__ = "requests"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="pending")

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="requests")

class ConversationState(Base):
    __tablename__ = "conversation_states"

    phone_number: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[ConversationStatus] = mapped_column(SAEnum(ConversationStatus), default=ConversationStatus.IDLE)
    draft_data: Mapped[Optional[dict]] = mapped_column(JSON)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
