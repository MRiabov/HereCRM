from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.database import Base
import enum

class DocumentType(str, enum.Enum):
    INTERNAL = "internal"
    CUSTOMER_UPLOAD = "customer_upload"
    GENERATED = "generated"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    filename: Mapped[str] = mapped_column(String)
    s3_key: Mapped[str] = mapped_column(String)
    public_url: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    doc_type: Mapped[DocumentType] = mapped_column(SAEnum(DocumentType), default=DocumentType.INTERNAL)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(back_populates="documents")
