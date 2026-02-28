import pytest
from unittest.mock import patch
from src.services.invoice_service import InvoiceService
from src.models import Job, Business

pytestmark = pytest.mark.asyncio

async def test_invoice_create_lazy_load_bug(async_session):
    # Setup
    biz = Business(name="Test Biz", default_tax_rate=10.0, workflow_tax_inclusive=True)
    async_session.add(biz)
    await async_session.flush()

    from src.models import Customer
    cust = Customer(name="Test Cust", business_id=biz.id)
    async_session.add(cust)
    await async_session.flush()

    job = Job(business_id=biz.id, customer_id=cust.id, description="Test job", value=100.0)
    async_session.add(job)
    await async_session.commit()

    # Store the ID to fetch later
    job_id = job.id

    service = InvoiceService(async_session)

    with patch("src.services.pdf_generator.PDFGenerator.generate_invoice", return_value=b"pdf"):
        with patch("src.services.storage.S3Service.upload_file", return_value="https://s3.url"):
            # Load the job WITHOUT relationships to simulate the bug scenario
            # (which is what happens normally when a simple query fetches the job)
            job_no_rels = await async_session.get(Job, job_id)

            # Since create_invoice now uses selectinload internally by querying the db with the job.id,
            # this should succeed without throwing a MissingGreenlet or DetachedInstanceError.
            inv = await service.create_invoice(job_no_rels)
            assert inv is not None
