from src.models import RequestStatus, UserRole, JobStatus
import pytest
from src.models import Business, Job, Customer, User, Request, PipelineStage
from src.tool_executor import ToolExecutor
from src.uimodels import (
    AddJobTool,
    AddLeadTool,
    ConvertRequestTool,
    SearchTool,
    GetPipelineTool,
)
from src.services.template_service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def template_service():
    return TemplateService()


@pytest.mark.asyncio
async def test_execute_add_job_new_customer(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    from unittest.mock import MagicMock, patch, AsyncMock

    # Mock GeocodingService to prevent unclosed client sessions
    with (
        patch("src.events.event_bus.emit", new_callable=AsyncMock),
        patch("src.tool_executor.GeocodingService") as link_mock,
        patch("src.services.crm_service.GeocodingService") as crm_mock,
    ):
        mock_geo = MagicMock()
        mock_geo.geocode = AsyncMock(
            return_value=(None, None, None, None, None, None, None)
        )

        link_mock.return_value = mock_geo
        crm_mock.return_value = mock_geo

        executor = ToolExecutor(
            test_session, biz.id, user.id, user.phone_number, template_service
        )
        tool = AddJobTool(
            customer_name="Alice",
            customer_phone="5551234",
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
    assert customer.phone == "5551234"

    res = await test_session.execute(select(Job).where(Job.customer_id == customer.id))
    job = res.scalar_one()
    assert job.description == "Wash windows"
    assert job.value == 100.0


@pytest.mark.asyncio
async def test_execute_convert_request(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    # Pre-existing request
    req = Request(
        business_id=biz.id,
        description="I want to fix my roof",
        status=RequestStatus.PENDING,
    )
    test_session.add(req)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )
    tool = ConvertRequestTool(query="roof", action="SCHEDULE", time="tomorrow")

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
    assert job.status == JobStatus.SCHEDULED


@pytest.mark.asyncio
async def test_execute_log_request(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    # Pre-existing request
    req = Request(
        business_id=biz.id,
        description="Info only request",
        status=RequestStatus.PENDING,
    )
    test_session.add(req)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )
    tool = ConvertRequestTool(query="Info", action="LOG")

    result, metadata = await executor.execute(tool)

    assert "Request logged" in result
    assert metadata["action"] == "update"

    # Verify status changed but request still exists
    from sqlalchemy import select

    res = await test_session.execute(select(Request).where(Request.id == req.id))
    updated_req = res.scalar_one()
    assert updated_req.status == RequestStatus.LOGGED


@pytest.mark.asyncio
async def test_execute_add_lead_implicit(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )

    # 1. Add Lead
    tool = AddLeadTool(
        name="Bob The Lead",
        phone="5551234",
        details="Just inquiring",
    )
    result, metadata = await executor.execute(tool)

    assert "Lead details:" in result
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
    search_tool = SearchTool(query="leads", detailed=True)
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
    result, _ = await executor.execute(search_tool)
    if result and "No results found" not in result:
        assert "Bob The Lead" not in result


@pytest.mark.asyncio
async def test_deduplication(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Dedupe Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )

    # 1. Add Customer Case-Sensitive
    tool = AddLeadTool(name="John Doe", phone="5550000")
    await executor.execute(tool)

    # 2. Add Job with Case-Insensitive Name
    job_tool = AddJobTool(
        customer_name="john doe", description="Fix window", price=50.0
    )
    result, metadata = await executor.execute(job_tool)
    assert "John Doe" in result

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


@pytest.mark.asyncio
async def test_execute_get_pipeline(
    async_session: AsyncSession, template_service: TemplateService
):
    test_session = async_session
    biz = Business(name="Pipeline Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123456789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    # Add a customer to have something in the pipeline
    c1 = Customer(
        name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED
    )
    test_session.add(c1)
    await test_session.flush()

    executor = ToolExecutor(
        test_session, biz.id, user.id, user.phone_number, template_service
    )
    tool = GetPipelineTool()

    result, metadata = await executor.execute(tool)

    assert "### Pipeline Breakdown" in result
    assert "Alice" in result
    assert metadata["action"] == "query"
    assert metadata["entity"] == "pipeline"
