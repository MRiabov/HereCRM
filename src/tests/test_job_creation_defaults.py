import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.crm_service import CRMService
from src.models import Business, Customer

@pytest.mark.asyncio
async def test_create_job_defaults(session: AsyncSession):
    # Setup business and customer
    business = Business(name="Test Biz")
    session.add(business)
    await session.flush()
    
    customer = Customer(name="Test Cust", business_id=business.id)
    session.add(customer)
    await session.flush()
    
    service = CRMService(session, business_id=business.id)
    
    # Test 1: Explicit description
    job1 = await service.create_job(
        customer_id=customer.id,
        description="Explicit Title"
    )
    assert job1.description == "Explicit Title"
    
    # Test 2: None description
    job2 = await service.create_job(
        customer_id=customer.id,
        description=None
    )
    assert job2.description == f"Job #{job2.id}"
    
    # Test 3: Empty string description
    job3 = await service.create_job(
        customer_id=customer.id,
        description="   "
    )
    assert job3.description == f"Job #{job3.id}"
