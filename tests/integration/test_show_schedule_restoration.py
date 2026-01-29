import pytest
from datetime import date, timedelta
from src.models import Business, Job, Customer, User, UserRole, JobStatus
from src.tool_executor import ToolExecutor
from src.tools.employee_management import ShowScheduleTool
from src.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.fixture
def template_service():
    return TemplateService()


@pytest.mark.asyncio
async def test_execute_show_schedule(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Schedule Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(
        name="John Tech",
        phone_number="123456789",
        business_id=biz.id,
        role=UserRole.MANAGER,
    )
    test_session.add(user)
    await test_session.flush()

    # Create Customer
    customer = Customer(name="Schedule Customer", business_id=biz.id)
    test_session.add(customer)
    await test_session.flush()

    # Scheduled Job
    today = date.today()
    job1 = Job(
        business_id=biz.id,
        customer_id=customer.id,
        description="Scheduled Job",
        status=JobStatus.SCHEDULED,
        scheduled_at=today,
        employee_id=user.id,
    )
    test_session.add(job1)

    # Unscheduled Job
    job2 = Job(
        business_id=biz.id,
        customer_id=customer.id,
        description="Unscheduled Job",
        status=JobStatus.PENDING,
    )
    test_session.add(job2)
    await test_session.flush()

    # Mock GeocodingService etc as needed by ToolExecutor
    with (
        patch("src.events.event_bus.emit", new_callable=AsyncMock),
        patch("src.tool_executor.GeocodingService") as link_mock,
        patch("src.services.crm_service.GeocodingService") as crm_mock,
    ):
        mock_geo = MagicMock()
        mock_geo.geocode = AsyncMock(
            return_value=(None, None, None, None, None, None, None)
        )
        link_mock.return_value = mock_geo
        crm_mock.return_value = mock_geo

        executor = ToolExecutor(
            test_session, biz.id, user.id, user.phone_number, template_service
        )

        # Execute Tool
        tool = ShowScheduleTool(date=today.isoformat())
        result, metadata = await executor.execute(tool)

        # Verification
        print(f"Result: {result}")
        print(f"Metadata: {metadata}")

        # Check Text Output
        assert "Daily Schedule" in result
        assert "John Tech" in result
        assert "Scheduled Job" in result
        assert "Unscheduled Job" in result

        # Check Metadata
        assert metadata["action"] == "query"
        assert metadata["entity"] == "schedule_report"
        assert metadata["date"] == today.isoformat()

        # Check Employees in Metadata
        employees_data = metadata["employees"]
        assert len(employees_data) >= 1
        found_tech = False
        for emp in employees_data:
            if emp["name"] == "John Tech":
                found_tech = True
                assert len(emp["jobs"]) == 1
                assert emp["jobs"][0]["description"] == "Scheduled Job"
        assert found_tech

        # Check Unscheduled in Metadata
        unscheduled_data = metadata["UNSCHEDULED"]
        assert len(unscheduled_data) == 1
        assert unscheduled_data[0]["description"] == "Unscheduled Job"
