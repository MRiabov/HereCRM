import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.crm_service import CRMService
from src.models import Urgency

@pytest.mark.asyncio
async def test_request_creation_with_items(session: AsyncSession):
    # Create business
    from src.models import Business
    business = Business(name="Test Business")
    session.add(business)
    await session.flush()
    business_id = business.id
    
    crm = CRMService(session, business_id=business_id)
    
    # Define items
    items = [
        {"description": "Item 1", "quantity": 2, "unit_price": 50.0},
        {"description": "Item 2", "quantity": 1, "unit_price": 100.0}
    ]
    
    # Create request
    request = await crm.create_request(
        description="Test Request with items",
        items=items,
        urgency=Urgency.HIGH,
        subtotal=200.0,
        tax_amount=20.0,
        tax_rate=0.1
    )
    
    assert request.id is not None
    assert len(request.line_items) == 2
    assert request.expected_value == 200.0
    assert request.subtotal == 200.0
    assert request.tax_amount == 20.0
    assert request.tax_rate == 0.1
    assert request.line_items[0].description == "Item 1"
    assert request.line_items[0].total_price == 100.0

@pytest.mark.asyncio
async def test_convert_request_to_job_preserves_items(session: AsyncSession):
    # Create business
    from src.models import Business
    business = Business(name="Test Business")
    session.add(business)
    await session.flush()
    business_id = business.id

    crm = CRMService(session, business_id=business_id)
    
    # 1. Create a customer
    from src.models import Customer
    customer = Customer(name="Test Customer", business_id=business_id, phone="123456789", email="test@example.com", street="123 Main St", city="Dublin", country="Ireland", postal_code="D1")
    session.add(customer)
    await session.flush()
    
    # 2. Create a request with items
    items = [{"description": "Service 1", "quantity": 1, "unit_price": 150.0}]
    request = await crm.create_request(
        description="Convert me",
        customer_id=customer.id,
        items=items,
        subtotal=150.0
    )
    
    # 3. Convert to Job
    msg, metadata = await crm.convert_request(query="Test Customer", action="schedule")
    
    assert metadata["entity"] == "job"
    job_id = metadata["id"]
    
    # 4. Verify Job has items
    from src.repositories import JobRepository
    job_repo = JobRepository(session)
    job = await job_repo.get_with_line_items(job_id, business_id)
    
    assert len(job.line_items) == 1
    assert job.line_items[0].description == "Service 1"
    assert job.value == 150.0

@pytest.mark.asyncio
async def test_convert_request_to_quote_preserves_items(session: AsyncSession):
    # Create business
    from src.models import Business
    business = Business(name="Test Business")
    session.add(business)
    await session.flush()
    business_id = business.id

    crm = CRMService(session, business_id=business_id)
    
    # 1. Create a customer
    from src.models import Customer
    customer = Customer(name="Quote Customer", business_id=business_id, phone="987654321", email="quote@example.com", street="123 Main St", city="Dublin", country="Ireland", postal_code="D1")
    session.add(customer)
    await session.flush()
    
    # 2. Create a request with items
    items = [{"description": "Quote Item", "quantity": 1, "unit_price": 500.0}]
    request = await crm.create_request(
        description="Quote me",
        customer_id=customer.id,
        items=items,
        subtotal=500.0
    )
    
    # 3. Convert to Quote
    msg, metadata = await crm.convert_request(query="Quote Customer", action="quote")
    
    assert metadata["entity"] == "quote"
    quote_id = metadata["id"]
    
    # 4. Verify Quote has items
    quote = await crm.quote_service.get_quote(quote_id)
    # quote_service.get_quote doesn't joinedload items by default in its current impl?
    # Let's check QuoteService.get_quote
    
    from sqlalchemy.orm import selectinload
    from src.models import Quote
    from sqlalchemy import select
    stmt = select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id)
    result = await session.execute(stmt)
    quote = result.scalars().first()
    
    assert len(quote.items) == 1
    assert quote.items[0].description == "Quote Item"
    assert quote.total_amount == 500.0
