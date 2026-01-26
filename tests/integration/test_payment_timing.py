import pytest
from src.models import Business, Customer, User, PaymentTiming
from src.services.crm_service import CRMService

@pytest.mark.asyncio
async def test_job_creation_respects_payment_timing(async_session):
    """
    Verifies that create_job defaults 'paid' status based on business settings.
    """
    
    # 1. Setup Business
    business = Business(name="Payment Test Biz", workflow_payment_timing=PaymentTiming.PAID_LATER)
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="Test Customer", business_id=business.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    crm_service = CRMService(async_session, business.id)

    # 2. Test Case 1: PAID_LATER -> paid should be False
    job1 = await crm_service.create_job(customer_id=customer.id, description="Paid Later Job")
    assert job1.paid is False

    # 3. Test Case 2: USUALLY_PAID_ON_SPOT -> paid should be True (New Logic)
    business.workflow_payment_timing = PaymentTiming.USUALLY_PAID_ON_SPOT
    await async_session.commit() 
    
    job2 = await crm_service.create_job(customer_id=customer.id, description="Usually Paid Job")
    assert job2.paid is True

    # 4. Test Case 3: ALWAYS_PAID_ON_SPOT -> paid should be True
    business.workflow_payment_timing = PaymentTiming.ALWAYS_PAID_ON_SPOT
    await async_session.commit()
    
    job3 = await crm_service.create_job(customer_id=customer.id, description="Always Paid Job")
    assert job3.paid is True

    print("\n✅ Payment Timing Logic Verified Successfully!")
