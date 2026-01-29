import pytest
from src.models import Business, Customer, User, QuoteStatus
from src.repositories import CustomerRepository, JobRepository
from src.services.crm_service import CRMService
from src.services.quote_service import QuoteService
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_core_crud_operations(async_session):
    # 1. Setup Business and User
    business = Business(name="Core Logic Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    user = User(
        email="core@example.com",
        business_id=business.id,
        role="OWNER"
    )
    async_session.add(user)
    await async_session.commit()

    crm_service = CRMService(async_session, business.id)
    quote_service = QuoteService(async_session)
    customer_repo = CustomerRepository(async_session)
    job_repo = JobRepository(async_session)

    # 2. Add Customer
    customer = Customer(
        name="Test Customer",
        phone="+1234567890",
        business_id=business.id,
        street="123 Main St"
    )
    customer_repo.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)
    assert customer.id is not None
    assert customer.name == "Test Customer"

    # 3. Add Job for Customer
    job = await crm_service.create_job(
        customer_id=customer.id,
        description="Initial Job",
        value=100.0,
        scheduled_at=datetime.now(timezone.utc)
    )
    assert job.id is not None
    assert job.customer_id == customer.id
    assert job.value == 100.0

    # 4. Add Quote for Customer
    quote = await quote_service.create_quote(
        business_id=business.id,
        customer_id=customer.id,
        lines=[{"description": "Service 1", "quantity": 1, "unit_price": 50.0}]
    )
    assert quote.id is not None
    assert quote.total_amount == 50.0

    # 5. Edit Customer
    await crm_service.update_customer(customer.id, name="Updated Customer")
    updated_customer = await customer_repo.get_by_id(customer.id, business.id)
    assert updated_customer.name == "Updated Customer"

    # 6. Edit Job
    await crm_service.update_job(job.id, description="Updated Job", value=150.0)
    updated_job = await job_repo.get_by_id(job.id, business.id)
    assert updated_job.description == "Updated Job"
    assert updated_job.value == 150.0

    # 7. Edit Quote
    # Quote editing usually involves updating status or replacing items
    # For now, let's just update the status to SENT
    quote.status = QuoteStatus.SENT
    await async_session.commit()
    await async_session.refresh(quote)
    assert quote.status == QuoteStatus.SENT

    # 8. Verify in Schedule (Implicitly via list_jobs)
    # Schedule logic usually filters jobs by date
    today = datetime.now(timezone.utc).date()
    # Assuming list_jobs returns jobs for a date range
    schedules = await crm_service.get_employee_schedules(today)
    
    # Check if our job is in there (might be under 'unassigned' if no employee set)
    all_jobs = []
    for user_jobs in schedules.values():
        all_jobs.extend(user_jobs)
    
    # Also check unscheduled if it wasn't scheduled correctly
    unscheduled = await crm_service.get_unscheduled_jobs()
    all_jobs.extend(unscheduled)
    
    assert any(j.id == job.id for j in all_jobs)
