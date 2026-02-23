import pytest
from unittest.mock import AsyncMock, MagicMock
from src.models import Job, LineItem, Business, Customer
from src.services.invoice_service import InvoiceService
from datetime import datetime

@pytest.mark.asyncio
async def test_invoice_tax_snapshot(async_session):
    # Setup Data
    business = Business(name="Test Biz", default_tax_rate=0.10) # 10% tax
    async_session.add(business)
    await async_session.flush()

    customer = Customer(name="Test Cust", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()

    job = Job(
        business_id=business.id,
        customer_id=customer.id,
        description="Test Job"
    )
    async_session.add(job)
    await async_session.flush()

    li1 = LineItem(job_id=job.id, description="Item 1", quantity=1.0, unit_price=100.0, total_price=100.0)
    li2 = LineItem(job_id=job.id, description="Item 2", quantity=2.0, unit_price=50.0, total_price=100.0)
    async_session.add_all([li1, li2])
    await async_session.flush()

    # Refresh to load relationships
    await async_session.refresh(job, attribute_names=["line_items", "business", "customer"])

    # Initialize Service
    service = InvoiceService(async_session)

    # Mock PDF Generator and S3
    service.pdf_generator = MagicMock()
    service.pdf_generator.generate_invoice.return_value = b"pdf_content"

    service.s3_service = MagicMock()
    service.s3_service.upload_file.return_value = "http://s3.url/invoice.pdf"

    # Execute
    invoice = await service.create_invoice(job)

    # Verify Invoice Fields
    assert invoice.subtotal == 200.0
    assert invoice.tax_rate == 0.10
    assert invoice.tax_amount == 20.0
    assert invoice.total_amount == 220.0

    # Verify Job Snapshot
    assert job.subtotal == 200.0
    assert job.tax_amount == 20.0
    assert job.value == 220.0

    # Verify PDF Call
    service.pdf_generator.generate_invoice.assert_called_once()
    call_kwargs = service.pdf_generator.generate_invoice.call_args.kwargs
    assert call_kwargs["subtotal"] == 200.0
    assert call_kwargs["tax_amount"] == 20.0
    assert call_kwargs["tax_rate"] == 0.10
    assert call_kwargs["total_amount"] == 220.0

@pytest.mark.asyncio
async def test_invoice_tax_snapshot_manual_items(async_session):
    # Setup Data
    business = Business(name="Test Biz", default_tax_rate=0.05) # 5% tax
    async_session.add(business)
    await async_session.flush()

    customer = Customer(name="Test Cust", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()

    job = Job(
        business_id=business.id,
        customer_id=customer.id,
        description="Test Job"
    )
    async_session.add(job)
    await async_session.flush()
    await async_session.refresh(job, attribute_names=["business", "customer"])

    # Initialize Service
    service = InvoiceService(async_session)

    # Mock PDF Generator and S3
    service.pdf_generator = MagicMock()
    service.pdf_generator.generate_invoice.return_value = b"pdf_content"
    service.s3_service = MagicMock()
    service.s3_service.upload_file.return_value = "http://s3.url/invoice.pdf"

    # Manual Items
    items = [
        {"description": "Manual Item 1", "quantity": 10.0, "unit_price": 10.0}, # 100
    ]

    # Execute
    invoice = await service.create_invoice(job, items=items)

    # Verify Invoice Fields
    assert invoice.subtotal == 100.0
    assert invoice.tax_rate == 0.05
    assert invoice.tax_amount == 5.0
    assert invoice.total_amount == 105.0

    # Verify Job Snapshot
    assert job.subtotal == 100.0
    assert job.tax_amount == 5.0
    assert job.value == 105.0
