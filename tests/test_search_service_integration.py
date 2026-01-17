import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from src.database import Base
from src.services.search_service import SearchService
from src.services.geocoding import GeocodingService
from src.uimodels import SearchTool
from src.models import Business, User, Customer, Job, Request

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
def mock_geocoding_service():
    service = MagicMock(spec=GeocodingService)
    # Default to returning None
    service.geocode = AsyncMock(return_value=(None, None, None, None, None))
    return service

@pytest_asyncio.fixture
async def search_service(db_session, mock_geocoding_service):
    return SearchService(db_session, mock_geocoding_service)

@pytest_asyncio.fixture
async def setup_data(db_session: AsyncSession):
    # Business
    bus = Business(name="Test Biz")
    db_session.add(bus)
    await db_session.flush()

    # User
    user = User(phone_number="123", business_id=bus.id)
    db_session.add(user)

    # Coordinates
    DUBLIN_LAT, DUBLIN_LON = 53.3498, -6.2603
    LONDON_LAT, LONDON_LON = 51.5074, -0.1278
    CORK_LAT, CORK_LON = 51.8985, -8.4756

    # Customers
    # c1: Dublin
    c1 = Customer(name="Dublin Customer", business_id=bus.id, latitude=DUBLIN_LAT, longitude=DUBLIN_LON)
    # c2: London
    c2 = Customer(name="London Customer", business_id=bus.id, latitude=LONDON_LAT, longitude=LONDON_LON)
    # c3: Cork (No Job)
    c3 = Customer(name="Cork Lead", business_id=bus.id, latitude=CORK_LAT, longitude=CORK_LON)
    
    db_session.add_all([c1, c2, c3])
    await db_session.flush()

    # Jobs
    # j1: Dublin (at c1 location implicitly via customer linkage, but we set explicit null to test fallback if we want, or explicit match)
    # Let's give specific location slightly offset
    j1 = Job(
        description="Dublin Job", 
        business_id=bus.id, 
        customer_id=c1.id, 
        latitude=DUBLIN_LAT, 
        longitude=DUBLIN_LON,
        status="pending"
    )

    # j2: London Job
    j2 = Job(
        description="London Job", 
        business_id=bus.id, 
        customer_id=c2.id, 
        latitude=LONDON_LAT, 
        longitude=LONDON_LON,
        status="pending"
    )

    db_session.add_all([j1, j2])
    
    # Request (No location)
    r1 = Request(content="Site visit request", business_id=bus.id)
    db_session.add(r1)

    await db_session.commit()
    return bus.id

@pytest.mark.asyncio
async def test_search_proximity_job_filtering(search_service, setup_data):
    business_id = setup_data
    
    # Search near London (should return London Job, exclude Dublin Job)
    params = SearchTool(
        query="all",
        entity_type="job",
        center_lat=51.5074,
        center_lon=-0.1278,
        radius=5000.0 # 5km
    )
    
    result = await search_service.search(params, business_id=business_id)
    assert "London Job" in result
    assert "Dublin Job" not in result

@pytest.mark.asyncio
async def test_search_proximity_customer_filtering(search_service, setup_data):
    business_id = setup_data
    
    # Search near Dublin (should return Dublin Customer, exclude London/Cork)
    params = SearchTool(
        query="all",
        entity_type="customer",
        center_lat=53.3498,
        center_lon=-6.2603,
        radius=5000.0 # 5km
    )
    
    result = await search_service.search(params, business_id=business_id)
    assert "Dublin Customer" in result
    assert "London Customer" not in result
    assert "Cork Lead" not in result

@pytest.mark.asyncio
async def test_search_proximity_generic_aggregation(search_service, setup_data):
    business_id = setup_data
    
    # Generic search near London
    # Should find London Customer AND London Job.
    params = SearchTool(
        query="all",
        # entity_type=None,
        center_lat=51.5074,
        center_lon=-0.1278,
        radius=5000.0
    )
    
    result = await search_service.search(params, business_id=business_id)
    assert "London Customer" in result
    assert "London Job" in result
    assert "Dublin Customer" not in result
    assert "Dublin Job" not in result
    # Requests are currently NOT spatially filtered (RequestRepository.search doesn't take params),
    # so they might appear if query matches? But "all" is ignored?
    # RequestRepository.search logic: if query is "all" it matches everything?
    # Check RequestRepository:
    # if query and query.strip().lower() not in ["all", ...]: conditions.append(ilike)
    # So if "all", it returns ALL requests. AND it doesn't filter by location.
    # So "Site visit request" should BE in the result.
    assert "Site visit request" in result

@pytest.mark.asyncio
async def test_search_with_geocoding_trigger(search_service, setup_data, mock_geocoding_service):
    business_id = setup_data
    
    # Mock Geocoding response for "London"
    mock_geocoding_service.geocode.return_value = (51.5074, -0.1278, "Street", "City", "Country")
    
    params = SearchTool(
        query="all",
        center_address="London",
        # radius defaults to 200m in service if not provided
        radius=10000.0 # Wide radius
    )
    
    result = await search_service.search(params, business_id=business_id)
    
    # Check geocode was called
    mock_geocoding_service.geocode.assert_awaited_once_with("London")
    
    # Check fallback logic worked (found London items)
    assert "London Job" in result
    assert "Dublin Job" not in result
