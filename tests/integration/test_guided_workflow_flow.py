import pytest
from datetime import datetime, date, timedelta
from src.models import Job, Customer, User, UserRole, Business, Service, LineItem
from src.tool_executor import ToolExecutor
from src.uimodels import CompleteJobTool
from src.services.template_service import TemplateService

@pytest.fixture
def mock_template_service():
    class MockTemplateService:
        def render(self, template_name, **kwargs):
            return "Rendered Template"
    return MockTemplateService()

@pytest.mark.asyncio
async def test_complete_job_flow(async_session, mock_template_service):
    # Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.flush()
    
    employee = User(
        business_id=business.id,
        name="John Tech",
        role=UserRole.MEMBER,
        phone_number="1234567890"
    )
    async_session.add(employee)
    await async_session.flush()
    
    customer = Customer(business_id=business.id, name="Test Cust")
    async_session.add(customer)
    await async_session.flush()

    today = date.today()
    
    # Job 1: To be completed
    job1 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee.id,
        status="pending",
        location="123 Done St",
        scheduled_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=9)
    )
    
    # Job 2: Next up
    job2 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee.id,
        status="pending",
        location="456 Next St",
        latitude=53.3498,
        longitude=-6.2603,
        scheduled_at=datetime.combine(today, datetime.min.time()) + timedelta(hours=14)
    )
    
    service = Service(business_id=business.id, name="Test Service", default_price=100.0, reminder_text="Don't forget the ladder")
    async_session.add(service)
    await async_session.flush()
    
    line_item = LineItem(service_id=service.id, description="Work", unit_price=100.0, total_price=100.0, quantity=1.0)
    job2.line_items.append(line_item)
    
    async_session.add_all([job1, job2])
    await async_session.commit()

    # Create Executor
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=employee.id,
        user_phone=employee.phone_number,
        template_service=mock_template_service
    )
    
    # Act: Complete Job 1
    tool = CompleteJobTool(job_id=job1.id, notes="All good")
    response, data = await executor.execute(tool)
    
    # Refresh job1 to check status
    await async_session.refresh(job1)
    
    # Assert
    assert job1.status == "completed"
    assert "Job #{} marked as completed".format(job1.id) in response
    
    # Verify proactive guidance
    assert "Next up: Test Cust at 456 Next St" in response
    assert "Don't forget the ladder" in response # Reminder text
    assert "https://www.google.com/maps" in response # Map link

@pytest.mark.asyncio
async def test_complete_job_permission_denied(async_session, mock_template_service):
    # Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.flush()
    
    other_employee = User(
        business_id=business.id,
        name="Other Tech",
        role=UserRole.MEMBER
    )
    current_user = User(
        business_id=business.id,
        name="Me",
        role=UserRole.MEMBER,
        phone_number="00000000"
    )
    async_session.add_all([other_employee, current_user])
    await async_session.flush()
    
    customer = Customer(business_id=business.id, name="Test Cust")
    async_session.add(customer)
    await async_session.flush()

    job1 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=other_employee.id, # Assigned to OTHER
        status="pending"
    )
    async_session.add(job1)
    await async_session.commit()
    
    # Create Executor as 'Me'
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=current_user.id,
        user_phone=current_user.phone_number,
        template_service=mock_template_service
    )
    
    # Act
    tool = CompleteJobTool(job_id=job1.id)
    response, data = await executor.execute(tool)
    
    # Assert
    assert "Permission denied" in response
    await async_session.refresh(job1)
    assert job1.status == "pending"

@pytest.mark.asyncio
async def test_complete_job_owner_override(async_session, mock_template_service):
    # Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.flush()
    
    employee = User(business_id=business.id, name="Tech", role=UserRole.MEMBER)
    owner = User(business_id=business.id, name="Boss", role=UserRole.OWNER, phone_number="999999999")
    async_session.add_all([employee, owner])
    await async_session.flush()
    
    customer = Customer(business_id=business.id, name="Test Cust")
    async_session.add(customer)
    await async_session.flush()

    job1 = Job(
        business_id=business.id,
        customer_id=customer.id,
        employee_id=employee.id, # Assigned to Employee
        status="pending"
    )
    async_session.add(job1)
    await async_session.commit()
    
    # Create Executor as 'Boss' (Owner)
    executor = ToolExecutor(
        session=async_session,
        business_id=business.id,
        user_id=owner.id,
        user_phone=owner.phone_number,
        template_service=mock_template_service
    )
    
    # Act
    tool = CompleteJobTool(job_id=job1.id)
    response, data = await executor.execute(tool)
    
    # Assert
    await async_session.refresh(job1)
    assert job1.status == "completed"
    assert "marked as completed" in response
