from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String,
    ForeignKey,
    DateTime,
    Text,
    Float,
    Enum as SAEnum,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from src.models.base_enum import RobustEnum, SafeSAEnum
from src.database import Base

if TYPE_CHECKING:
    from src.models import Business, Customer


class CampaignStatus(RobustEnum):
    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    SENDING = "SENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class RecipientStatus(RobustEnum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELETED = "DELETED"


class CampaignChannel(RobustEnum):
    WHATSAPP = "WHATSAPP"
    EMAIL = "EMAIL"
    SMS = "SMS"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            for member in cls:
                if member.value.upper() == value.upper():
                    return member
        return None


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    channel: Mapped[CampaignChannel] = mapped_column(SafeSAEnum(CampaignChannel))
    status: Mapped[CampaignStatus] = mapped_column(
        SafeSAEnum(CampaignStatus), default=CampaignStatus.DRAFT
    )

    # Template/Content
    template_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )  # For WhatsApp HSM or similar
    subject: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # For Email
    body: Mapped[str] = mapped_column(Text)

    # Targeting
    recipient_query: Mapped[Optional[str]] = mapped_column(
        String
    )  # Natural language or JSON filter

    # Metrics
    total_recipients: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    business: Mapped["Business"] = relationship("Business", back_populates="campaigns")
    recipients: Mapped[List["CampaignRecipient"]] = relationship(
        "CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan"
    )


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    status: Mapped[RecipientStatus] = mapped_column(
        SafeSAEnum(RecipientStatus), default=RecipientStatus.PENDING
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata for the specific send (e.g. message ID from provider)
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="recipients")
    customer: Mapped["Customer"] = relationship("Customer")
