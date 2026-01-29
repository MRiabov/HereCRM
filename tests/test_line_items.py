import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Service, Job, LineItem, Customer
from src.services.inference_service import InferenceService
from src.uimodels import LineItemInfo

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
async def test_rounding_precision(test_session: AsyncSession):
    # Test that intermediate calculations are rounded and consistent
    business = Business(name="Rounding Test")
    test_session.add(business)
    await test_session.flush()

    service = Service(
        business_id=business.id, name="Precise Service", default_price=10.0
    )
    test_session.add(service)
    await test_session.flush()

    inference_service = InferenceService(test_session)

    # Case: Total price 13.33, default price 10.0 -> Quantity should be 1.33
    # 1.33 * 10.0 = 13.30. The total_price should be adjusted to 13.30 to maintain consistency with rounded quantity.
    raw_items = [LineItemInfo(description="Precise Service", total_price=13.33)]
    items = await inference_service.infer_line_items(business.id, raw_items)

    assert len(items) == 1
    item = items[0]
    assert item.quantity == 1.33
    assert item.unit_price == 10.0
    assert item.total_price == 13.30  # Consistent with 1.33 * 10.0


@pytest.mark.asyncio
async def test_snapshotting_integrity(test_session: AsyncSession):
    # Test that historical jobs preserve their prices even if catalog changes
    business = Business(name="Snapshot Test")
    test_session.add(business)
    await test_session.flush()

    service = Service(
        business_id=business.id, name="Fixed Price Service", default_price=50.0
    )
    test_session.add(service)
    await test_session.flush()

    customer = Customer(business_id=business.id, name="Test Customer")
    test_session.add(customer)
    await test_session.flush()

    # Create job with line item
    job = Job(
        business_id=business.id,
        customer_id=customer.id,
        description="Old Job",
        value=50.0,
    )
    line_item = LineItem(
        job=job,
        service_id=service.id,
        description=service.name,
        quantity=1.0,
        unit_price=50.0,
        total_price=50.0,
    )
    test_session.add(job)
    test_session.add(line_item)
    await test_session.flush()

    # Change catalog price
    service.default_price = 75.0
    await test_session.flush()

    # Verify existing job line item still has old price
    assert line_item.unit_price == 50.0
    assert line_item.total_price == 50.0


@pytest.mark.asyncio
async def test_negative_validation(test_session: AsyncSession):
    # Test SQLAlchemy validators
    business = Business(name="Validation Test")
    test_session.add(business)
    await test_session.flush()

    # Negative service price
    with pytest.raises(ValueError, match="Service price cannot be negative"):
        Service(business_id=business.id, name="Bad Service", default_price=-10.0)

    # Negative line item quantity
    with pytest.raises(ValueError, match="Quantity cannot be negative"):
        LineItem(
            description="Bad Item", quantity=-1.0, unit_price=10.0, total_price=-10.0
        )

    # Negative job value
    customer = Customer(business_id=business.id, name="Test Customer")
    test_session.add(customer)
    await test_session.flush()

    with pytest.raises(ValueError, match="Job value cannot be negative"):
        Job(business_id=business.id, customer_id=customer.id, value=-100.0)


@pytest.mark.asyncio
async def test_job_value_synchronization(test_session: AsyncSession):
    # Test that Job value is automatically updated when line items are added
    business = Business(name="Sync Test")
    test_session.add(business)
    await test_session.flush()

    customer = Customer(business_id=business.id, name="Test Customer")
    test_session.add(customer)
    await test_session.flush()

    job = Job(
        business_id=business.id, customer_id=customer.id, description="Job", value=0.0
    )
    test_session.add(job)
    await test_session.flush()

    # Add line items
    li1 = LineItem(
        job_id=job.id,
        description="Item 1",
        quantity=1,
        unit_price=10.0,
        total_price=10.0,
    )
    li2 = LineItem(
        job_id=job.id,
        description="Item 2",
        quantity=2,
        unit_price=20.0,
        total_price=40.0,
    )
    test_session.add(li1)
    test_session.add(li2)
    await test_session.flush()

    # Refresh job
    await test_session.refresh(job)
    assert job.value == 50.0

    # Update line item
    li1.total_price = 15.0
    await test_session.flush()
    await test_session.refresh(job)
    assert job.value == 55.0

    # Delete line item
    await test_session.delete(li2)
    await test_session.flush()
    await test_session.refresh(job)
    assert job.value == 15.0
