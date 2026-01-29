import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, User, Job, Service
from src.services.availability_service import AvailabilityService

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


@pytest.mark.asyncio
async def test_add_availability(test_session: AsyncSession):
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    customer = Customer(business_id=biz.id, name="John")
    test_session.add(customer)
    await test_session.flush()

    service = AvailabilityService(test_session)
    start = datetime.now()
    end = start + timedelta(hours=2)

    avail = await service.add_availability(customer.id, start, end)
    assert avail.id is not None
    assert avail.customer_id == customer.id


@pytest.mark.asyncio
async def test_availability_overlap(test_session: AsyncSession):
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    customer = Customer(business_id=biz.id, name="John")
    test_session.add(customer)
    await test_session.flush()

    service = AvailabilityService(test_session)
    now = datetime.now()

    # Available from 9:00 to 11:00
    start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end = now.replace(hour=11, minute=0, second=0, microsecond=0)
    await service.add_availability(customer.id, start, end, is_available=True)

    # Check 9:30 to 10:30 (Available)
    assert (
        await service.is_customer_available(
            customer.id, start + timedelta(minutes=30), start + timedelta(minutes=90)
        )
        == True
    )

    # Check 11:00 to 12:00 (Not Available - no window covers it)
    assert (
        await service.is_customer_available(customer.id, end, end + timedelta(hours=1))
        == False
    )

    # Add 'unavailable' override from 10:00 to 10:30
    unavail_start = start + timedelta(hours=1)
    unavail_end = start + timedelta(hours=1, minutes=30)
    await service.add_availability(
        customer.id, unavail_start, unavail_end, is_available=False
    )

    # Check 10:15 (Unavailable now because of override)
    assert (
        await service.is_customer_available(
            customer.id,
            unavail_start + timedelta(minutes=5),
            unavail_start + timedelta(minutes=10),
        )
        == False
    )


@pytest.mark.asyncio
async def test_model_fields(test_session: AsyncSession):
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(
        name="Worker",
        business_id=biz.id,
        default_start_location_lat=45.0,
        default_start_location_lng=9.0,
    )
    test_session.add(user)

    job = Job(business_id=biz.id, customer_id=1, estimated_duration=120)
    test_session.add(job)

    svc = Service(
        business_id=biz.id, name="Svc", default_price=100, estimated_duration=45
    )
    test_session.add(svc)

    await test_session.commit()

    assert user.default_start_location_lat == 45.0
    assert job.estimated_duration == 120
    assert svc.estimated_duration == 45
