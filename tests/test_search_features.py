import pytest
from datetime import datetime, timedelta, timezone
from src.models import Job, Customer, Request, User, Business, JobStatus, EntityType
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.tool_executor import ToolExecutor
from src.uimodels import SearchTool
from src.database import Base
from src.services.template_service import TemplateService
from unittest.mock import AsyncMock
import pytest_asyncio

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
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
def mock_template_service():
    return TemplateService()


# Mock data setup
@pytest.fixture
async def setup_search_data(db_session: AsyncSession):
    # Create Business
    business = Business(name="Test Business")
    db_session.add(business)
    await db_session.flush()

    # Create User with Timezone
    user = User(phone_number="1234567890", business_id=business.id, timezone="UTC")
    db_session.add(user)

    # Create Customers
    c1 = Customer(
        name="John Doe",
        phone="085111222",
        business_id=business.id,
        created_at=datetime.now(timezone.utc),
        street="123 Main St",
        city="Dublin",
        latitude=53.3498,
        longitude=-6.2603,
    )
    c2 = Customer(
        name="Jane Smith",
        phone="086111333",
        business_id=business.id,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        street="456 High Street",
        city="London",
        latitude=51.5074,
        longitude=-0.1278,
    )
    c3 = Customer(
        name="Bob Lead",
        phone="087111444",
        business_id=business.id,
        created_at=datetime.now(timezone.utc),
        street="789 Low Road",
        city="Cork",
    )
    db_session.add_all([c1, c2, c3])
    await db_session.flush()

    # Create Jobs
    j1 = Job(
        customer_id=c1.id,
        business_id=business.id,
        description="Window cleaning",
        status=JobStatus.PENDING,
        scheduled_at=datetime.now(timezone.utc).replace(
            hour=14, minute=0, second=0, microsecond=0
        ),
        created_at=datetime.now(timezone.utc),
        location="123 Main St",
        latitude=53.3498,
        longitude=-6.2603,
    )
    j2 = Job(
        customer_id=c2.id,
        business_id=business.id,
        description="Gutter cleaning",
        status=JobStatus.SCHEDULED,
        scheduled_at=(datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=10, minute=0, second=0, microsecond=0
        ),
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
        location="456 High Street",
        latitude=51.5074,
        longitude=-0.1278,
    )
    db_session.add_all([j1, j2])

    # Create Requests
    r1 = Request(
        business_id=business.id,
        description="Call back later",
        status=JobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(r1)

    await db_session.commit()
    return business.id, user.id, "1234567890"


@pytest.mark.asyncio
async def test_search_jobs_today(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    today_start = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    today_end = (
        datetime.now(timezone.utc)
        .replace(hour=23, minute=59, second=59, microsecond=0)
        .isoformat()
    )

    tool = SearchTool(
        query="all",
        entity_type=EntityType.JOB,
        query_type="SCHEDULED",
        min_date=today_start,
        max_date=today_end,
    )

    result, _ = await executor.execute(tool)
    assert "Window cleaning" in result
    assert "Gutter cleaning" not in result


@pytest.mark.asyncio
async def test_search_jobs_tomorrow(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    tomorrow_start = (
        (datetime.now(timezone.utc) + timedelta(days=1))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    tomorrow_end = (
        (datetime.now(timezone.utc) + timedelta(days=1))
        .replace(hour=23, minute=59, second=59, microsecond=0)
        .isoformat()
    )

    tool = SearchTool(
        query="all",
        entity_type=EntityType.JOB,
        query_type="SCHEDULED",
        min_date=tomorrow_start,
        max_date=tomorrow_end,
    )

    result, _ = await executor.execute(tool)
    assert "Gutter cleaning" in result
    assert "Window cleaning" not in result


@pytest.mark.asyncio
async def test_search_customers_with_jobs_today(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    today_start = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    today_end = (
        datetime.now(timezone.utc)
        .replace(hour=23, minute=59, second=59, microsecond=0)
        .isoformat()
    )

    tool = SearchTool(
        query="all",
        entity_type=EntityType.CUSTOMER,
        query_type="SCHEDULED",
        min_date=today_start,
        max_date=today_end,
    )

    result, _ = await executor.execute(tool)
    assert "John Doe" in result
    assert "Jane Smith" not in result


@pytest.mark.asyncio
async def test_search_leads_added_today(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    today_start = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat()
    )
    today_end = (
        datetime.now(timezone.utc)
        .replace(hour=23, minute=59, second=59, microsecond=0)
        .isoformat()
    )

    tool = SearchTool(
        query="all",
        entity_type=EntityType.LEAD,
        query_type="ADDED",
        min_date=today_start,
        max_date=today_end,
    )

    result, _ = await executor.execute(tool)
    assert "Bob Lead" in result
    assert "John Doe" not in result
    assert "Jane Smith" not in result


@pytest.mark.asyncio
async def test_search_text_fallback(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    tool = SearchTool(query="John")
    result, _ = await executor.execute(tool)
    assert "John Doe" in result


@pytest.mark.asyncio
async def test_search_empty_results(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    tool = SearchTool(query="NonExistent")
    result, _ = await executor.execute(tool)
    assert "No results found" in result


@pytest.mark.asyncio
async def test_search_geo(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )

    tool = SearchTool(query="High Street")
    result, _ = await executor.execute(tool)

    assert "Jane Smith" in result
    assert "Gutter cleaning" in result
    assert "John Doe" not in result


@pytest.mark.asyncio
async def test_search_geo_proximity(
    db_session: AsyncSession, setup_search_data, mock_template_service
):
    business_id, user_id, user_phone = setup_search_data
    executor = ToolExecutor(
        db_session, business_id, user_id, user_phone, mock_template_service
    )
    # Mock GeocodingService
    mock_geo = AsyncMock()
    mock_geo.geocode.return_value = (None, None, None, None, None, None, None)
    executor.search_service.geocoding_service = mock_geo

    tool = SearchTool(
        query="all", center_lat=51.5074, center_lon=-0.1278, radius=1000.0
    )
    result, _ = await executor.execute(tool)
    assert "Jane Smith" in result
    assert "John Doe" not in result

    tool_addr = SearchTool(
        query="all",
        center_address="High Street",
        radius=5000.0,
    )
    mock_geo.geocode.return_value = (
        51.5074,
        -0.1278,
        None,
        None,
        None,
        None,
        "High Street",
    )
    result_addr, _ = await executor.execute(tool_addr)
    assert "Jane Smith" in result_addr
