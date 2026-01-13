import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Customer, Request
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool, ConvertRequestTool

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    
    await engine.dispose()

@pytest.mark.asyncio
async def test_execute_add_job_new_customer(test_session: AsyncSession):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()
    
    executor = ToolExecutor(test_session, biz.id)
    tool = AddJobTool(
        customer_name="Alice",
        customer_phone="555-1234",
        description="Wash windows",
        price=100.0,
        location="123 Street"
    )
    
    result, metadata = await executor.execute(tool)
    
    assert "Job added: Alice" in result
    assert metadata["action"] == "create"
    
    # Verify DB
    from sqlalchemy import select
    res = await test_session.execute(select(Customer).where(Customer.name == "Alice"))
    customer = res.scalar_one()
    assert customer.phone == "555-1234"
    
    res = await test_session.execute(select(Job).where(Job.customer_id == customer.id))
    job = res.scalar_one()
    assert job.description == "Wash windows"
    assert job.value == 100.0

@pytest.mark.asyncio
async def test_execute_convert_request(test_session: AsyncSession):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()
    
    # Pre-existing request
    req = Request(business_id=biz.id, content="I want to fix my roof", status="pending")
    test_session.add(req)
    await test_session.flush()
    
    executor = ToolExecutor(test_session, biz.id)
    tool = ConvertRequestTool(
        query="roof",
        action="schedule",
        time="tomorrow"
    )
    
    result, metadata = await executor.execute(tool)
    
    assert "Converted Request to Job" in result
    assert metadata["action"] == "promote"
    
    # Verify request deleted and job created
    from sqlalchemy import select
    res = await test_session.execute(select(Request).where(Request.id == req.id))
    assert res.scalar_one_or_none() is None
    
    res = await test_session.execute(select(Job))
    job = res.scalar_one()
    assert "Converted from request: I want to fix my roof" in job.description
    assert job.status == "scheduled"
