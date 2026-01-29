import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Customer, User, UserRole, JobStatus
from src.tool_executor import ToolExecutor
from src.uimodels import CheckETATool
from src.services.template_service import TemplateService
from src.services.location_service import LocationService
from datetime import datetime, timezone

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with SessionLocal() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def template_service():
    return TemplateService()


@pytest.mark.asyncio
async def test_check_eta_tool_redundant_query(
    test_session: AsyncSession, template_service: TemplateService
):
    # Setup Data
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    owner = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(owner)

    # Technician with location
    tech = User(
        name="Tech Bob",
        phone_number="987654321",
        business_id=biz.id,
        role=UserRole.EMPLOYEE,
        current_latitude=40.7128,
        current_longitude=-74.0060,
        location_updated_at=datetime.now(timezone.utc),
    )
    test_session.add(tech)

    customer = Customer(
        name="Alice",
        phone="5551234",
        business_id=biz.id,
        latitude=40.730610,
        longitude=-73.935242,
    )
    test_session.add(customer)
    await test_session.flush()

    job = Job(
        customer_id=customer.id,
        business_id=biz.id,
        employee_id=tech.id,
        description="Fix sink",
        status=JobStatus.SCHEDULED,
        scheduled_at=datetime.now(timezone.utc),
        estimated_duration=60,
        latitude=40.730610,
        longitude=-73.935242,
    )
    test_session.add(job)
    await test_session.flush()

    # Create Executor
    executor = ToolExecutor(
        test_session, biz.id, owner.id, owner.phone_number, template_service
    )

    # Mock Routing Service to avoid external calls
    mock_routing = MagicMock()
    mock_routing.get_eta_minutes.return_value = 15
    executor._routing_service = mock_routing

    # Spy on LocationService.get_employee_location
    with patch(
        "src.services.location_service.LocationService.get_employee_location",
        side_effect=LocationService.get_employee_location,
    ) as mock_get_loc:
        tool = CheckETATool(customer_query="Alice")
        result, metadata = await executor.execute(tool)

        assert "approximately 15 minutes away" in result
        assert metadata["action"] == "check_eta"
        assert metadata["tech_name"] == "Tech Bob"

        # Verify optimization: should be 0 calls as we access attributes directly
        assert mock_get_loc.call_count == 0, (
            "LocationService.get_employee_location should not be called"
        )
