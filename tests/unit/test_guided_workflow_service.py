import pytest
from datetime import datetime, date, timedelta
from src.models import Job, Customer, Service, LineItem, Business
from src.services.guided_workflow_service import GuidedWorkflowService

@pytest.mark.asyncio
async def test_get_next_job_for_employee_found(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.flush()
    
    customer = Customer(name="Test Cust", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()
    
    employee_id = 1
    today = date.today()
    
    # Create jobs for today
    job1 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee_id,
        status="pending",
        scheduled_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=10)
    )
    job2 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee_id,
        status="pending",
        scheduled_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=14)
    )
    
    async_session.add_all([job1, job2])
    await async_session.commit()
    
    # Execute
    next_job = await GuidedWorkflowService.get_next_job_for_employee(async_session, employee_id)
    
    # Verify - should find the earliest job
    assert next_job is not None
    assert next_job.scheduled_at == datetime.combine(today, datetime.min.time()) + timedelta(hours=10)

@pytest.mark.asyncio
async def test_get_next_job_for_employee_none_left(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.flush()
    
    customer = Customer(name="Test Cust", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()
    
    employee_id = 2
    today = date.today()
    
    # Completed job for today
    job1 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee_id,
        status="completed",
        scheduled_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=10)
    )
    
    async_session.add(job1)
    await async_session.commit()
    
    # Execute
    next_job = await GuidedWorkflowService.get_next_job_for_employee(async_session, employee_id)
    
    # Verify
    assert next_job is None

@pytest.mark.asyncio
async def test_get_next_job_for_employee_only_future_days(async_session):
    # Setup
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.flush()
    
    customer = Customer(name="Test Cust", business_id=business.id)
    async_session.add(customer)
    await async_session.flush()
    
    employee_id = 3
    tomorrow = date.today() + timedelta(days=1)
    
    # Job for tomorrow
    job1 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee_id,
        status="pending",
        scheduled_at=datetime.combine(tomorrow, datetime.min.time()) + timedelta(hours=10)
    )
    
    async_session.add(job1)
    await async_session.commit()
    
    # Execute
    next_job = await GuidedWorkflowService.get_next_job_for_employee(async_session, employee_id)
    
    # Verify - should only find jobs for today
    assert next_job is None

def test_format_next_job_message_with_reminders():
    # Setup
    customer = Customer(name="John Doe")
    service1 = Service(name="Window Cleaning", reminder_text="Bring extra towels")
    service2 = Service(name="Gutter Cleaning", reminder_text="Check the back downspout")
    
    job = Job(
        location="123 Main St",
        latitude=40.7128,
        longitude=-74.0060,
        customer=customer
    )
    
    item1 = LineItem(service=service1)
    item2 = LineItem(service=service2)
    job.line_items = [item1, item2]
    
    # Execute
    message = GuidedWorkflowService.format_next_job_message(job)
    
    # Verify
    assert "Next up: John Doe at 123 Main St" in message
    assert "https://www.google.com/maps/search/?api=1&query=40.7128,-74.006" in message
    assert "Reminders:" in message
    assert "- Bring extra towels" in message
    assert "- Check the back downspout" in message

def test_format_next_job_message_no_reminders():
    # Setup
    customer = Customer(name="Jane Smith")
    job = Job(
        location="456 Elm St",
        customer=customer
    )
    job.line_items = []
    
    # Execute
    message = GuidedWorkflowService.format_next_job_message(job)
    
    # Verify
    assert "Next up: Jane Smith at 456 Elm St" in message
    assert "Map Link:" in message
    assert "Reminders:" not in message
