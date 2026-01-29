import pytest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, UserRole, Job, Customer, JobStatus
from src.tool_executor import ToolExecutor
from src.uimodels import AutorouteTool
from src.services.routing.base import RoutingSolution, RoutingStep
from datetime import date, datetime


@pytest.fixture
def mock_routing_service():
    mock = MagicMock()
    return mock


@pytest.fixture
def template_service():
    mock = MagicMock()
    mock.render.side_effect = lambda key, **kwargs: f"Rendered {key} {kwargs}"
    return mock


@pytest.mark.asyncio
async def test_autoroute_preview_success(
    session: AsyncSession, mock_routing_service, template_service, monkeypatch
):
    # Setup Data
    # 1. Employee
    emp = User(
        email="tech@example.com",
        role=UserRole.EMPLOYEE,
        business_id=1,
        phone_number="123456",
        default_start_location_lat=53.3,
        default_start_location_lng=-6.2,
    )
    session.add(emp)

    # 2. Customer & Jobs
    cust = Customer(name="Test Cust", business_id=1, latitude=53.33, longitude=-6.22)
    session.add(cust)
    await session.flush()

    # Job scheduled for today
    today = date.today()
    job = Job(
        customer_id=cust.id,
        business_id=1,
        description="Fix sink",
        status=JobStatus.SCHEDULED,
        scheduled_at=datetime.combine(today, datetime.min.time()),
        latitude=53.33,
        longitude=-6.22,
    )
    session.add(job)
    await session.commit()

    # Setup ToolExecutor
    executor = ToolExecutor(
        session,
        business_id=1,
        user_id=1,
        user_phone="123",
        template_service=template_service,
    )

    # Patch settings to simulate API key present
    settings_mock = MagicMock()
    settings_mock.openrouteservice_api_key = "fake_key"
    monkeypatch.setattr("src.tools.routing_tools.settings", settings_mock)

    # Patch the Adapter class to return our mock instance
    mock_adapter_cls = MagicMock(return_value=mock_routing_service)
    monkeypatch.setattr(
        "src.tools.routing_tools.OpenRouteServiceAdapter", mock_adapter_cls
    )

    # Configure mock return value for `calculate_routes`
    solution = RoutingSolution(
        routes={emp.id: [RoutingStep(job=job)]},
        unassigned_jobs=[],
        metrics={"distance": 5000, "duration": 1800},
    )
    mock_routing_service.calculate_routes.return_value = solution

    # Act
    tool = AutorouteTool(date=today.isoformat(), apply=False, notify=True)
    result, metadata = await executor.execute(tool)

    # Assert
    assert "Rendered autoroute_preview" in result
    assert "Total Distance: 5.0 km" in result
    assert "Est. Time: 0.5 hrs" in result
    assert "Test Cust" in result
    assert "Fix sink" in result
    assert metadata is not None
    assert metadata["action"] == "preview_route"

    # Verify service called
    mock_routing_service.calculate_routes.assert_called_once()
