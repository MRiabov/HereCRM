from src.models import InvoiceStatus
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime

from src.models import Job, Invoice
from src.services.storage import S3Service, StorageError
from src.services.pdf_generator import PDFGenerator
from src.services.tax_calculator import tax_calculator

logger = logging.getLogger(__name__)


class InvoiceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.s3_service = S3Service()
        self.pdf_generator = PDFGenerator()

    async def get_existing_invoice(self, job_id: int) -> Optional[Invoice]:
        """
        Retrieves the most recent invoice for a given job.
        """
        stmt = (
            select(Invoice)
            .where(Invoice.job_id == job_id)
            .order_by(desc(Invoice.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_invoice(
        self,
        job: Job,
        force_regenerate: bool = False,
        invoice_number: Optional[str] = None,
        issued_at: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        items: Optional[list] = None,
    ) -> Invoice:
        """
        Creates a new invoice for the job.
        If an invoice already exists and force_regenerate is False, returns the existing one.
        """
        if not force_regenerate:
            existing = await self.get_existing_invoice(job.id)
            if existing:
                logger.info(f"Returning existing invoice for job {job.id}")
                return existing

        logger.info(f"Generating new invoice for job {job.id}")

        # 0. Fetch payment link snapshot from business
        payment_link = job.business.payment_link if job.business else None

        # 0.5 Calculate Taxes
        if items:
            # Use provided items
            calc_lines = items
        else:
            # Use job line items
            calc_lines = [
                {
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "description": item.description,
                }
                for item in job.line_items
            ]

        tax_result = tax_calculator.calculate_quote_tax(
            calc_lines, job.business, job.customer
        )

        # Update Job snapshot (only if we are using job items, strictly speaking,
        # but spec says snapshot on invoice generation usually updates job too or reflects it)
        # However, if 'items' are custom, we shouldn't necessarily update the job's master record
        # unless we want the job to reflect what was invoiced.
        # Let's assuming for now we update job snapshot values always for consistency.
        job.subtotal = tax_result["subtotal"]
        job.tax_amount = tax_result["tax_amount"]
        job.tax_rate = tax_result["tax_rate"]
        # job.value usually tracks the total value
        job.value = tax_result["total_amount"]

        # 1. Generate PDF
        try:
            pdf_bytes = self.pdf_generator.generate_invoice(
                job,
                invoice_date=issued_at,
                payment_link=payment_link,
                invoice_number=invoice_number,
                due_date=due_date,
                notes=notes,
                items=items,
                subtotal=tax_result["subtotal"],
                tax_amount=tax_result["tax_amount"],
                tax_rate=tax_result["tax_rate"],
                total_amount=tax_result["total_amount"],
            )
        except (ValueError, RuntimeError) as e:
            logger.error(f"Failed to generate PDF for job {job.id}: {e}")
            raise RuntimeError(f"PDF generation failed: {e}") from e

        # 2. Upload to S3
        filename = f"invoices/invoice_{job.id}_{int(datetime.now().timestamp())}.pdf"
        try:
            public_url = self.s3_service.upload_file(
                file_content=pdf_bytes, key=filename, content_type="application/pdf"
            )
        except StorageError as e:
            logger.error(f"S3 upload failed for job {job.id}: {e}")
            raise RuntimeError(f"S3 upload failed: {e}") from e

        # 3. Save to Database
        invoice = Invoice(
            job_id=job.id,
            s3_key=filename,
            public_url=public_url,
            payment_link=payment_link,
            status=InvoiceStatus.GENERATED,
            subtotal=tax_result["subtotal"],
            tax_amount=tax_result["tax_amount"],
            tax_rate=tax_result["tax_rate"],
            total_amount=tax_result["total_amount"],
        )
        self.session.add(invoice)
        await self.session.flush()

        return invoice
