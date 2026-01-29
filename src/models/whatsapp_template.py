from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from src.database import Base


class WhatsAppTemplateStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    DRAFT = "DRAFT"  # Local only


class WhatsAppTemplateCategory(str, enum.Enum):
    MARKETING = "MARKETING"
    UTILITY = "UTILITY"
    AUTHENTICATION = "AUTHENTICATION"


class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)

    name: Mapped[str] = mapped_column(String, index=True)
    language: Mapped[str] = mapped_column(String, default="en_US")
    category: Mapped[WhatsAppTemplateCategory] = mapped_column(
        SAEnum(WhatsAppTemplateCategory)
    )

    # Store the components structure as defined by Meta API (BODY, HEADER, FOOTER, BUTTONS)
    components: Mapped[Any] = mapped_column(JSON)

    status: Mapped[WhatsAppTemplateStatus] = mapped_column(
        SAEnum(WhatsAppTemplateStatus), default=WhatsAppTemplateStatus.DRAFT
    )

    # Meta specific
    meta_template_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    business = relationship("Business", back_populates="whatsapp_templates")
