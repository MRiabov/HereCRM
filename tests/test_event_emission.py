import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool, ScheduleJobTool
from src.models import Customer, Job, Business, User, UserRole, JobStatus
from src.services.template_service import TemplateService


@pytest.mark.asyncio
async def test_add_job_emits_event(async_session: AsyncSession):
    test_session = async_session
    # Setup
    business = Business(name="Test Biz")
    test_session.add(business)
    await test_session.flush()

    user_id = 999
    user = User(
        id=user_id,
        business_id=business.id,
        role=UserRole.OWNER,
        phone_number="1234567890",
    )
    test_session.add(user)
    await test_session.flush()

    user_phone = "1234567890"
    template_service = AsyncMock(spec=TemplateService)
    template_service.render.return_value = "Mocked Template"

    # Mock event bus and GeocodingService to prevent background tasks and unclosed sessions
    with (
        patch("src.events.event_bus.emit", new_callable=AsyncMock) as mock_emit,
        patch("src.tool_executor.GeocodingService") as MockGeoTool,
        patch("src.services.crm_service.GeocodingService") as MockGeoCRM,
    ):
        # Configure mocks
        MockGeoTool.return_value.geocode = AsyncMock(
            return_value=(None, None, None, None, None, None, None)
        )
        MockGeoCRM.return_value.geocode = AsyncMock(
            return_value=(None, None, None, None, None, None, None)
        )

        executor = ToolExecutor(
            test_session, business.id, user_id, user_phone, template_service
        )

        # Execute
        tool = AddJobTool(
            customer_name="Test Customer",
            customer_phone="1987654321",
            description="Test Job",
            location="Test Location",
            price=100.0,
            status=JobStatus.PENDING,
        )

        await executor.execute(tool)

        # Verify JOB_CREATED was emitted (from CRMService)
        found = False
        for call in mock_emit.call_args_list:
            if call[0][0] == "JOB_CREATED":
                found = True
                data = call[0][1]
                assert data["business_id"] == business.id
                break
        assert found, "JOB_CREATED event not emitted"


@pytest.mark.asyncio
async def test_schedule_job_emits_event(async_session: AsyncSession):
    test_session = async_session
    # Setup
    business = Business(name="Test Biz")
    test_session.add(business)
    await test_session.flush()

    user_id = 999
    user = User(
        id=user_id,
        business_id=business.id,
        role=UserRole.OWNER,
        phone_number="1234567890",
    )
    test_session.add(user)
    await test_session.flush()

    user_phone = "1234567890"
    template_service = AsyncMock(spec=TemplateService)
    template_service.render.return_value = "Mocked Template"

    # Create existing job and customer
    customer = Customer(
        business_id=business.id, name="Test Customer", phone="1987654321"
    )
    test_session.add(customer)
    await test_session.flush()

    job = Job(
        business_id=business.id,
        customer_id=customer.id,
        description="Test Job",
        status=JobStatus.PENDING,
    )
    test_session.add(job)
    await test_session.commit()

    # Mock event bus and GeocodingService
    with (
        patch("src.events.event_bus.emit", new_callable=AsyncMock) as mock_emit,
        patch("src.tool_executor.GeocodingService") as MockGeoTool,
        patch("src.services.crm_service.GeocodingService") as MockGeoCRM,
    ):
        MockGeoTool.return_value.geocode = AsyncMock(
            return_value=(None, None, None, None, None, None, None)
        )
        MockGeoCRM.return_value.geocode = AsyncMock(
            return_value=(None, None, None, None, None, None, None)
        )

        executor = ToolExecutor(
            test_session, business.id, user_id, user_phone, template_service
        )

        # Execute
        tool = ScheduleJobTool(
            job_id=job.id, time="Tomorrow at 2pm", iso_time="2026-01-16T14:00:00Z"
        )

        await executor.execute(tool)

        # Verify JOB_SCHEDULED was emitted
        found = False
        for call in mock_emit.call_args_list:
            if call[0][0] == "JOB_SCHEDULED":
                found = True
                data = call[0][1]
                assert data["job_id"] == job.id
                assert data["business_id"] == business.id
                assert "2026-01-16T14:00:00" in data["scheduled_at"]
                break
        assert found, "JOB_SCHEDULED event not emitted"
