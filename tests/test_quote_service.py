import pytest
from src.services.quote_service import QuoteService
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.models import QuoteStatus, Business, Customer, Job


@pytest.mark.asyncio
async def test_confirm_quote(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="John Doe", business_id=business.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    service = QuoteService(async_session)
    lines = [{"description": "Item 1", "quantity": 1.0, "unit_price": 50.0}]
    quote = await service.create_quote(customer.id, business.id, lines)

    # Execute
    confirmed = await service.confirm_quote(quote.external_token)

    # Verify
    assert confirmed.id == quote.id
    assert confirmed.status == QuoteStatus.ACCEPTED
    assert confirmed.job_id is not None

    # Verify Job creation
    stmt = (
        select(Job)
        .options(selectinload(Job.line_items))
        .where(Job.id == confirmed.job_id)
    )
    result = await async_session.execute(stmt)
    job = result.scalars().first()

    assert job is not None
    assert job.customer_id == customer.id
    assert job.business_id == business.id
    assert job.value == 50.0
    assert len(job.line_items) == 1
    assert job.line_items[0].description == "Item 1"


@pytest.mark.asyncio
async def test_create_quote(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="John Doe", business_id=business.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    service = QuoteService(async_session)
    lines = [
        {"description": "Item 1", "quantity": 2.0, "unit_price": 50.0},
        {"description": "Item 2", "quantity": 1.0, "unit_price": 100.0},
    ]

    # Execute
    quote = await service.create_quote(customer.id, business.id, lines)
    await async_session.refresh(quote, ["items"])

    # Verify
    assert quote.id is not None
    assert quote.total_amount == 200.0
    assert len(quote.items) == 2
    assert quote.status == QuoteStatus.DRAFT
    assert quote.external_token is not None
    assert quote.items[0].total == 100.0
    assert quote.items[1].total == 100.0


@pytest.mark.asyncio
async def test_get_quote(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="John Doe", business_id=business.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    service = QuoteService(async_session)
    quote = await service.create_quote(
        customer.id, business.id, [{"description": "Item 1", "unit_price": 50.0}]
    )

    # Execute
    retrieved = await service.get_quote(quote.id)

    # Verify
    assert retrieved.id == quote.id
    assert retrieved.total_amount == 50.0


@pytest.mark.asyncio
async def test_get_recent_quote(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="John Doe", business_id=business.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    service = QuoteService(async_session)

    # 1. Draft quote
    await service.create_quote(
        customer.id, business.id, [{"description": "Draft", "unit_price": 10.0}]
    )

    # 2. Sent quote
    quote_sent = await service.create_quote(
        customer.id, business.id, [{"description": "Sent", "unit_price": 20.0}]
    )
    quote_sent.status = QuoteStatus.SENT
    await async_session.commit()

    # Execute
    recent = await service.get_recent_quote(customer.id)

    # Verify
    assert recent.id == quote_sent.id
    assert recent.status == QuoteStatus.SENT
