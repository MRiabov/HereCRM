import pytest
from src.models import Business, Customer, Request, Quote, QuoteStatus, User
from src.services.crm_service import CRMService

@pytest.mark.asyncio
async def test_request_to_quote_promotion(async_session):
    # 1. Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(
        name="Alice", 
        phone="+111222333", 
        business_id=business.id
    )
    async_session.add(customer)
    
    # Include Alice in content so search works
    request = Request(
        business_id=business.id,
        description="Alice: I need a quote for a new terrace",
        status="PENDING"
    )
    async_session.add(request)
    await async_session.commit()
    await async_session.refresh(request)
    await async_session.refresh(customer)

    crm_service = CRMService(async_session, business.id)

    # 2. Promote Request to Quote
    msg, metadata = await crm_service.convert_request(
        query="Alice", # Identifying by query which matches content
        action="quote"
    )

    # 3. Verify Result
    assert "Converted Request to Quote" in msg
    assert metadata["action"] == "promote"
    assert metadata["entity"] == "quote"
    
    quote_id = metadata["id"]
    
    # Use joinedload to avoid MissingGreenlet
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    stmt = select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id)
    res = await async_session.execute(stmt)
    quote = res.scalar_one_or_none()
    
    assert quote is not None
    assert quote.customer_id == customer.id
    assert quote.status == QuoteStatus.DRAFT
    # Check that it has one line item with request content
    assert len(quote.items) == 1
    assert "Alice" in quote.items[0].description
    assert quote.items[0].unit_price == 0.0

    # 4. Verify Request is deleted (following existing promotion pattern)
    stmt = select(Request).where(Request.id == request.id)
    res = await async_session.execute(stmt)
    assert res.scalars().first() is None

@pytest.mark.asyncio
async def test_request_to_quote_promotion_with_id(async_session):
    # Testing that it finds request by content search
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="Bob", business_id=business.id)
    async_session.add(customer)
    
    request = Request(
        business_id=business.id,
        description="Bob: Fix my window please",
        status="PENDING"
    )
    async_session.add(request)
    await async_session.commit()

    crm_service = CRMService(async_session, business.id)

    # Promote using content query
    msg, metadata = await crm_service.convert_request(
        query="window",
        action="quote"
    )

    assert metadata["entity"] == "quote"
    quote_id = metadata["id"]
    
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    stmt = select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id)
    res = await async_session.execute(stmt)
    quote = res.scalar_one_or_none()
    
    assert quote is not None
    assert "window" in quote.items[0].description.lower()

@pytest.mark.asyncio
async def test_request_promotion_with_assigned_to_and_price(async_session):
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    employee = User(name="Jeff", business_id=business.id, role="employee")
    async_session.add(employee)
    await async_session.commit()
    await async_session.refresh(employee)

    customer = Customer(name="Charlie", business_id=business.id)
    async_session.add(customer)
    
    request = Request(
        business_id=business.id,
        description="Leaky faucet",
        status="PENDING"
    )
    async_session.add(request)
    await async_session.commit()

    crm_service = CRMService(async_session, business.id)

    # 1. Test Schedule (Job)
    msg, metadata = await crm_service.convert_request(
        query="faucet",
        action="schedule",
        assigned_to=employee.id,
        price=150.0
    )

    assert metadata["entity"] == "job"
    job_id = metadata["id"]
    
    from src.models import Job
    job = await async_session.get(Job, job_id)
    assert job.employee_id == employee.id
    assert job.value == 150.0

    # 2. Setup again for Quote
    request2 = Request(
        business_id=business.id,
        description="Garden work",
        status="PENDING"
    )
    async_session.add(request2)
    await async_session.commit()

    msg, metadata = await crm_service.convert_request(
        query="Garden",
        action="quote",
        price=500.0
    )

    assert metadata["entity"] == "quote"
    quote_id = metadata["id"]
    
    quote = await async_session.get(Quote, quote_id)
    assert quote.total_amount == 500.0
