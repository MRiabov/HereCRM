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
async def test_service_crud(test_session: AsyncSession):
    # Setup Business
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    repo = ServiceRepository(test_session)
    
    # ADD
    svc = Service(business_id=biz.id, name="Test Service", default_price=10.0)
    repo.add(svc)
    await test_session.commit()
    
    # GET
    assert svc.id is not None
    fetched = await repo.get_by_id(svc.id, biz.id)
    assert fetched is not None
    assert fetched.name == "Test Service"
    assert fetched.default_price == 10.0
    
    # UPDATE
    updated = await repo.update(svc.id, biz.id, default_price=12.5)
    assert updated is not None
    assert updated.default_price == 12.5
    await test_session.commit()
    
    # DELETE
    deleted = await repo.delete(svc.id, biz.id)
    assert deleted is True
    await test_session.commit()
    
    lookup = await repo.get_by_id(svc.id, biz.id)
    assert lookup is None

@pytest.mark.asyncio
async def test_job_with_line_items(test_session: AsyncSession):
    # Setup
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()
    
    cust = Customer(name="Cust", business_id=biz.id)
    test_session.add(cust)
    await test_session.flush()

    # Create Service
    svc = Service(business_id=biz.id, name="Window Clean", default_price=50.0)
    test_session.add(svc)
    await test_session.flush()

    # Create Job with Line Items
    job_repo = JobRepository(test_session)
    
    job = Job(
        business_id=biz.id, 
        customer_id=cust.id, 
        description="Job with lines"
    )
    
    # Add line items
    # Scenario: 2 Windows @ 50
    li1 = LineItem(description="Window Clean", quantity=2, unit_price=50.0, total_price=100.0, service_id=svc.id)
    # Scenario: 1 Gutter @ 30 (Ad-hoc)
    li2 = LineItem(description="Gutter", quantity=1, unit_price=30.0, total_price=30.0)
    
    job.line_items.append(li1)
    job.line_items.append(li2)
    
    # Test auto-calculation of value
    # value is None initially
    assert job.value is None
    
    job_repo.add(job)
    # The hook in repositories.py:add should calculate value
    assert job.value == 130.0
    
    await test_session.commit()
    
    # Test retrieval
    fetched_job = await job_repo.get_with_line_items(job.id, biz.id)
    assert fetched_job is not None
    assert len(fetched_job.line_items) == 2
    assert fetched_job.value == 130.0
    
    descriptions = sorted([li.description for li in fetched_job.line_items])
    assert descriptions == ["Gutter", "Window Clean"]
