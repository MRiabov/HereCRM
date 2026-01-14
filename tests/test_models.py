import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job
from src.repositories import JobRepository

# Use in-memory SQLite for tests
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
async def test_tenant_isolation(test_session: AsyncSession):
    # Setup Business A
    biz_a = Business(name="Biz A")
    test_session.add(biz_a)
    await test_session.flush()  # get IDs

    # Setup Business B
    biz_b = Business(name="Biz B")
    test_session.add(biz_b)
    await test_session.flush()

    # Create Job for A
    job_a = Job(
        business_id=biz_a.id, customer_id=1, description="Cleaning A", status="pending"
    )  # Mock customer ID
    test_session.add(job_a)

    # Create Job for B
    job_b = Job(
        business_id=biz_b.id, customer_id=2, description="Cleaning B", status="pending"
    )
    test_session.add(job_b)

    await test_session.commit()

    # Query using JobRepository for Biz A
    repo = JobRepository(test_session)
    jobs_a = await repo.get_all(business_id=biz_a.id)

    assert len(jobs_a) == 1
    assert jobs_a[0].description == "Cleaning A"
    assert jobs_a[0].business_id == biz_a.id

    # Verify we cannot see Job B
    job_lookup = await repo.get_by_id(id=job_b.id, business_id=biz_a.id)
    assert job_lookup is None


@pytest.mark.asyncio
async def test_message_log_creation(test_session: AsyncSession):
    from src.models import MessageLog, MessageType, MessageStatus

    log = MessageLog(
        recipient_phone="1234567890",
        content="Hello Test",
        message_type=MessageType.WHATSAPP,
        status=MessageStatus.PENDING,
        trigger_source="test_source",
    )
    test_session.add(log)
    await test_session.commit()

    # Query it back
    from sqlalchemy import select

    result = await test_session.execute(select(MessageLog).where(MessageLog.id == log.id))
    db_log = result.scalar_one()

    assert db_log.recipient_phone == "1234567890"
    assert db_log.content == "Hello Test"
    assert db_log.message_type == MessageType.WHATSAPP
    assert db_log.status == MessageStatus.PENDING
    assert db_log.created_at is not None
