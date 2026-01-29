import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Service, LineItem, Job, Customer
from src.repositories import ServiceRepository, JobRepository

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
async def test_service_crud_update(test_session: AsyncSession):
    # Setup Business
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    repo = ServiceRepository(test_session)

    # ADD
    svc = Service(business_id=biz.id, name="Test Service", default_price=10.0)
    repo.add(svc)
    await test_session.commit()

    # UPDATE - Secure
    # Try to update ID (should be ignored) and default_price (should be updated)
    # Removing business_id collision from test
    updated = await repo.update(svc.id, biz.id, default_price=12.5, id=999)
    assert updated is not None
    assert updated.default_price == 12.5
    assert updated.id != 999

    await test_session.commit()

    # Re-fetch to ensure persistence
    fetched = await repo.get_by_id(svc.id, biz.id)
    assert fetched.default_price == 12.5


@pytest.mark.asyncio
async def test_job_value_synchronization(test_session: AsyncSession):
    # Setup
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    cust = Customer(name="Cust", business_id=biz.id)
    test_session.add(cust)
    await test_session.flush()

    svc = Service(business_id=biz.id, name="Window Clean", default_price=50.0)
    test_session.add(svc)
    await test_session.flush()

    # Create Job
    job_repo = JobRepository(test_session)
    job = Job(business_id=biz.id, customer_id=cust.id, description="Job Sync Test")
    job_repo.add(job)
    await test_session.commit()

    # Verify initial value (None)
    assert job.value is None

    # 1. Add Line Item via Session directly (simulating repository usage or service layer)
    # Note: Event listener works on Flush.
    li1 = LineItem(
        job_id=job.id,
        description="Item 1",
        quantity=1,
        unit_price=100.0,
        total_price=100.0,
    )
    test_session.add(li1)
    await test_session.flush()  # Trigger events

    # Reload job to check value
    await test_session.refresh(job)
    assert job.value == 100.0

    # 2. Add another item
    li2 = LineItem(
        job_id=job.id,
        description="Item 2",
        quantity=2,
        unit_price=20.0,
        total_price=40.0,
    )
    test_session.add(li2)
    await test_session.flush()
    await test_session.refresh(job)
    assert job.value == 140.0

    # 3. Update an item
    li2.total_price = 50.0  # Changed price
    test_session.add(li2)  # Ensure it's in session
    await test_session.flush()
    await test_session.refresh(job)
    assert job.value == 150.0  # 100 + 50

    # 4. Delete an item
    await test_session.delete(li1)
    await test_session.flush()
    await test_session.refresh(job)
    assert job.value == 50.0
