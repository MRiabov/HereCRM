from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, JSON, Boolean, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import enum
import uuid
from src.database import Base

class IntegrationType(str, enum.Enum):
    INBOUND_KEY = "INBOUND_KEY"
    META_CAPI = "META_CAPI"
    WEBHOOK = "WEBHOOK"

class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    type: Mapped[IntegrationType] = mapped_column(SAEnum(IntegrationType), index=True)
    label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    key_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True, unique=True)
    config_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
