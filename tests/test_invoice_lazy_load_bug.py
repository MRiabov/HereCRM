import pytest
from unittest.mock import AsyncMock, patch
from src.services.invoice_service import InvoiceService
from src.models import Job, Business, JobStatus, Customer
from src.database import AsyncSessionLocal
from datetime import datetime

@pytest.mark.asyncio
async def test_invoice_creation_lazy_load_bug():
    # Setup
    with patch("src.services.invoice_service.S3Service") as MockS3, \
         patch("src.services.invoice_service.PDFGenerator") as MockPDF:

        mock_s3 = MockS3.return_value
        mock_s3.upload_file.return_value = "http://example.com/invoice.pdf"

        mock_pdf = MockPDF.return_value
        mock_pdf.generate_invoice.return_value = b"fake pdf content"

        async with AsyncSessionLocal() as session:
            # Create Business and Job
            business = Business(name="Test Biz", payment_link="http://pay.me")
            session.add(business)
            await session.flush()

            customer = Customer(business_id=business.id, name="Test Customer")
            session.add(customer)
            await session.flush()

            job = Job(
                business_id=business.id,
                customer_id=customer.id,
                status=JobStatus.COMPLETED
            )
            session.add(job)
            await session.commit()

            job_id = job.id
            business_id = business.id

        # New session to simulate request
        async with AsyncSessionLocal() as session:
            # Fetch job WITHOUT loading business relation explicitly
            # (default behavior)
            from src.repositories import JobRepository
            repo = JobRepository(session)
            job = await repo.get_by_id(job_id, business_id)

            assert job is not None

            # Initialize service
            service = InvoiceService(session)

            # Action: Create Invoice
            # This should fail if job.business is accessed without being loaded
            try:
                await service.create_invoice(job)
            except Exception as e:
                pytest.fail(f"Caught exception accessing job.business: {e}")
