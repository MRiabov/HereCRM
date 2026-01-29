import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.tool_executor import ToolExecutor
from src.uimodels import AddLeadTool, AddJobTool
from src.models import User, Business

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
async def setup_user(db_session):
    business = Business(name="Test Business")
    db_session.add(business)
    await db_session.flush()

    user = User(
        phone_number="1234567890",
        business_id=business.id,
        preferences={
            "default_city": "DefaultCity",
            "default_country": "DefaultCountry",
        },
    )
    db_session.add(user)
    await db_session.commit()
    return user, business.id


@pytest.mark.asyncio
async def test_add_lead_uses_defaults(db_session, setup_user):
    user, business_id = setup_user

    # Patch EventBus.emit to prevent background task interference with loop
    with patch("src.events.EventBus.emit", new_callable=AsyncMock) as mock_emit:
        # Mock GeocodingService
        with patch("src.tool_executor.GeocodingService") as MockGeo:
            mock_geo_instance = MockGeo.return_value

            async def side_effect(
                address, default_city=None, default_country=None, **kwargs
            ):
                city = default_city
                country = default_country
                return (
                    10.0,
                    20.0,
                    "Street",
                    city,
                    country,
                    "12345",
                    f"Street, {city}, {country}, 12345",
                )

            mock_geo_instance.geocode = AsyncMock(side_effect=side_effect)

            executor = ToolExecutor(
                db_session, business_id, user.id, user.phone_number, MagicMock()
            )

            # Test AddLeadTool with no specific location
            tool = AddLeadTool(name="Test Lead", location="Some Address")
            await executor.execute(tool)

            # Verify geocode was called with defaults
            mock_geo_instance.geocode.assert_called_with(
                "Some Address",
                default_city="DefaultCity",
                default_country="DefaultCountry",
                safeguard_enabled=False,
                max_distance_km=100.0,
            )

            # Verify customer created with defaults
            from src.repositories import CustomerRepository

            repo = CustomerRepository(db_session)
            customer = await repo.get_by_name("Test Lead", business_id)
            assert customer.city == "DefaultCity"
            assert customer.country == "DefaultCountry"


@pytest.mark.asyncio
async def test_add_job_creates_customer_with_defaults(db_session, setup_user):
    user, business_id = setup_user

    with patch("src.events.EventBus.emit", new_callable=AsyncMock) as mock_emit:
        with (
            patch("src.tool_executor.GeocodingService") as MockGeoTool,
            patch("src.services.crm_service.GeocodingService") as MockGeoCRM,
        ):
            mock_geo_instance = MockGeoTool.return_value
            mock_crm_instance = MockGeoCRM.return_value

            # Simulate geocoding returning defaults
            defaults = (
                1.0,
                2.0,
                "Street",
                "DefaultCity",
                "DefaultCountry",
                "54321",
                "Street, DefaultCity, DefaultCountry, 54321",
            )
            mock_geo_instance.geocode = AsyncMock(return_value=defaults)
            mock_crm_instance.geocode = AsyncMock(return_value=defaults)

            executor = ToolExecutor(
                db_session, business_id, user.id, user.phone_number, MagicMock()
            )

            # Test AddJobTool for new customer
            tool = AddJobTool(
                customer_name="New Customer", customer_phone="111", location="Test Loc"
            )
            await executor.execute(tool)

            # Verify geocode called on ToolExecutor's service
            mock_geo_instance.geocode.assert_any_call(
                "Test Loc",
                default_city="DefaultCity",
                default_country="DefaultCountry",
                safeguard_enabled=False,
                max_distance_km=100.0,
            )

            from src.repositories import CustomerRepository

            repo = CustomerRepository(db_session)
            customer = await repo.get_by_name("New Customer", business_id)
            assert customer
            assert customer.city == "DefaultCity"
            assert customer.country == "DefaultCountry"
