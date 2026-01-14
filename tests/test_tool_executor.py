import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Customer, Request
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool, AddLeadTool, ConvertRequestTool, SearchTool
from src.services.template_service import TemplateService

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
async def test_execute_add_job_new_customer(
    test_session: AsyncSession, template_service: TemplateService
):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, "123456789", template_service)
    tool = AddJobTool(
        customer_name="Alice",
        customer_phone="555-1234",
        description="Wash windows",
        price=100.0,
        location="123 Street",
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
async def test_execute_convert_request(
    test_session: AsyncSession, template_service: TemplateService
):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    # Pre-existing request
    req = Request(business_id=biz.id, content="I want to fix my roof", status="pending")
    test_session.add(req)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, "123456789", template_service)
    tool = ConvertRequestTool(query="roof", action="schedule", time="tomorrow")

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


@pytest.mark.asyncio
async def test_execute_log_request(
    test_session: AsyncSession, template_service: TemplateService
):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    # Pre-existing request
    req = Request(business_id=biz.id, content="Info only request", status="pending")
    test_session.add(req)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, "123456789", template_service)
    tool = ConvertRequestTool(query="Info", action="log")

    result, metadata = await executor.execute(tool)

    assert "Request logged" in result
    assert metadata["action"] == "update"

    # Verify status changed but request still exists
    from sqlalchemy import select

    res = await test_session.execute(select(Request).where(Request.id == req.id))
    updated_req = res.scalar_one()
    assert updated_req.status == "logged"


@pytest.mark.asyncio
async def test_execute_add_lead_implicit(
    test_session: AsyncSession, template_service: TemplateService
):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, "123456789", template_service)

    # 1. Add Lead
    tool = AddLeadTool(
        name="Bob The Lead",
        phone="555-LEAD",
        details="Just inquiring",
    )
    result, metadata = await executor.execute(tool)

    assert "Lead details:" in result  # Check for lead summary template usage
    assert "Bob The Lead" in result
    assert metadata["action"] == "create"
    assert metadata["entity"] == "lead"

    # Verify DB: Customer exists, NO Job
    from sqlalchemy import select

    res = await test_session.execute(
        select(Customer).where(Customer.name == "Bob The Lead")
    )
    customer = res.scalar_one()
    assert customer.details == "Just inquiring"

    res = await test_session.execute(select(Job).where(Job.customer_id == customer.id))
    assert res.scalar_one_or_none() is None

    # 2. Search Leads
    search_tool = SearchTool(query="leads")
    result, _ = await executor.execute(search_tool)
    assert "Bob The Lead" in result
    assert "Just inquiring" in result

    # 3. Convert to Customer (Add Job)
    job_tool = AddJobTool(
        customer_name="Bob The Lead",
        description="Real Job",
        price=100.0,
    )
    await executor.execute(job_tool)

    # 4. Search Leads again - should be empty (or at least not contain Bob)
    # Re-executing search
    result, _ = await executor.execute(search_tool)
    # The result could be "No results found" or a list not containing Bob
    if result and "No results found" not in result:
        assert "Bob The Lead" not in result


@pytest.mark.asyncio
async def test_deduplication(
    test_session: AsyncSession, template_service: TemplateService
):
    biz = Business(name="Dedupe Biz")
    test_session.add(biz)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, "123456789", template_service)

    # 1. Add Customer Case-Sensitive
    tool = AddLeadTool(name="John Doe", phone="555-0000")
    await executor.execute(tool)

    # 2. Add Job with Case-Insensitive Name
    job_tool = AddJobTool(
        customer_name="john doe", description="Fix window", price=50.0
    )
    result, metadata = await executor.execute(job_tool)
    assert "John Doe" in result  # Should refer to original name

    # 3. Verify only one customer exists
    from sqlalchemy import select, func

    res = await test_session.execute(select(func.count(Customer.id)))
    count = res.scalar()
    assert count == 1

    # Verify Job linked to existing customer
    res = await test_session.execute(select(Job))
    job = res.scalar_one()
    customer_res = await test_session.execute(
        select(Customer).where(Customer.id == job.customer_id)
    )
    customer = customer_res.scalar_one()
    assert customer.name == "John Doe"
