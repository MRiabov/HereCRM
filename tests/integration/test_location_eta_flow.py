import pytest
from unittest.mock import MagicMock, patch
from src.tool_executor import ToolExecutor
from src.uimodels import CheckETATool, LocateEmployeeTool
from src.models import User, Job, Customer, UserRole, Business
from src.services.location_service import LocationService
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_location_and_eta_flow(async_session):
    # Setup Data
    business = Business(name="Test Biz", id=1)
    async_session.add(business)
    await async_session.flush()

    # Admin User
    admin = User(business_id=1, name="Admin", role=UserRole.OWNER, phone_number="000111222")
    async_session.add(admin)

    # Tech User
    tech = User(
        business_id=1,
        name="John Tech",
        role=UserRole.EMPLOYEE,
        phone_number="999888777",
        current_latitude=53.34,
        current_longitude=-6.25,
        location_updated_at=datetime.now(timezone.utc)
    )
    async_session.add(tech)
    await async_session.flush()

    customer = Customer(
        business_id=1,
        name="Alice Client",
        phone="1234567890",
        latitude=53.30,
        longitude=-6.20
    )
    async_session.add(customer)
    await async_session.flush()

    # Job scheduled now
    now = datetime.now(timezone.utc)
    job = Job(
        business_id=1,
        customer_id=customer.id,
        employee_id=tech.id,
        scheduled_at=now,
        estimated_duration=60,
        latitude=53.30,
        longitude=-6.20,
        location="123 Test St",
        status="active"
    )
    async_session.add(job)
    await async_session.commit()

    template_service_mock = MagicMock()
    
    # Executor calls
    executor = ToolExecutor(
        async_session, 
        business_id=1, 
        user_id=admin.id, 
        user_phone="000111222", 
        template_service=template_service_mock
    )

    # 1. Test LocateEmployeeTool (Admin usage)
    locate_tool = LocateEmployeeTool(employee_name="John")
    resp, meta = await executor.execute(locate_tool)
    
    # Should find John Tech
    assert "John Tech" in resp
    assert "Live" in resp  # since location_updated_at is NOW
    assert "www.google.com/maps" in resp

    # Customer User (needed for RBAC check in ToolExecutor)
    alice_user = User(
        business_id=1,
        name="Alice Client",
        phone_number="1234567890",
        role=UserRole.EMPLOYEE # Customers acting as users need a role
    )
    async_session.add(alice_user)
    await async_session.flush()

    # 2. Test CheckETATool (Customer usage)
    # Re-init executor simulating customer call
    executor_customer = ToolExecutor(
        async_session, 
        business_id=1, 
        user_id=alice_user.id, 
        user_phone="1234567890", 
        template_service=template_service_mock
    )
    
    # Mock ORS
    with patch("src.tool_executor.OpenRouteServiceAdapter") as ORSMock:
        adapter_instance = ORSMock.return_value
        adapter_instance.get_eta_minutes.return_value = 15
        
        eta_tool = CheckETATool()
        resp_eta, meta_eta = await executor_customer.execute(eta_tool)
        
        assert "approximately 15 minutes away" in resp_eta
        assert "John Tech" in resp_eta
        assert meta_eta["eta_minutes"] == 15
