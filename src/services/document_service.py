import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Document, DocumentType
from src.services.storage import storage_service

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_document(
        self, 
        customer_id: int, 
        file_obj: bytes, 
        filename: str, 
        mime_type: str, 
        doc_type: DocumentType = DocumentType.INTERNAL
    ) -> Document:
        """
        Uploads file to storage and creates a Document record.
        """
        # Generate a unique key for S3
        # Structure: documents/{customer_id}/{uuid}_{filename}
        unique_id = str(uuid.uuid4())
        s3_key = f"documents/{customer_id}/{unique_id}_{filename}"
        
        try:
            public_url = storage_service.upload_file(
                file_content=file_obj,
                key=s3_key,
                content_type=mime_type
            )
        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            raise

        document = Document(
            customer_id=customer_id,
            filename=filename,
            s3_key=s3_key,
            public_url=public_url,
            mime_type=mime_type,
            doc_type=doc_type,
            created_at=datetime.now(timezone.utc)
        )
        
        self.session.add(document)
        await self.session.flush()
        
        return document
