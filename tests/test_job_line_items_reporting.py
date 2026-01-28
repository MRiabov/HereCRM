import pytest
from src.models import Job, Customer, User, Business, LineItem, Service
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from src.tool_executor import ToolExecutor
from src.uimodels import SearchTool, AddJobTool
from src.database import Base
from src.services.template_service import TemplateService
import pytest_asyncio

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
def template_service():
    return TemplateService()

@pytest.mark.asyncio
async def test_show_job_with_line_items(db_session: AsyncSession, template_service):
    # Setup
    business = Business(name="Test Business")
    db_session.add(business)
    await db_session.flush()

    user = User(phone_number="1234567890", business_id=business.id)
    db_session.add(user)
    
    svc = Service(name="Windows", default_price=50.0, business_id=business.id)
    db_session.add(svc)
    await db_session.flush()

    customer = Customer(name="John Doe", business_id=business.id)
    db_session.add(customer)
    await db_session.flush()

    job = Job(
        customer_id=customer.id,
        business_id=business.id,
        description="Clean windows",
        value=100.0,
        status=JobStatus.PENDING
    )
    db_session.add(job)
    await db_session.flush()

    li1 = LineItem(job_id=job.id, service_id=svc.id, quantity=2, unit_price=50.0, total_price=100.0, description="Windows")
    db_session.add(li1)
    await db_session.commit()

    executor = ToolExecutor(db_session, business_id=business.id, user_id=user.id, user_phone="1234567890", template_service=template_service)

    # Test Search (Detailed)
    search_tool = SearchTool(query="Clean windows", entity_type="job", detailed=True)
    result, _ = await executor.execute(search_tool)

    assert "Job: Clean windows" in result
    assert "Service    | Qty | Price | Total" in result
    assert "Windows" in result
    assert "2.0" in result
    assert "100.0" in result

@pytest.mark.asyncio
async def test_confirmation_with_line_items(db_session: AsyncSession, template_service):
    # Setup
    business = Business(name="Test Business")
    db_session.add(business)
    await db_session.flush()

    user = User(phone_number="1234567890", business_id=business.id)
    db_session.add(user)
    
    svc = Service(name="Gutter", default_price=30.0, business_id=business.id)
    db_session.add(svc)
    await db_session.commit()

    # We test via AddJobTool directly in ToolExecutor
    # Note: ToolExecutor._execute_add_job calls inference_service.infer_line_items
    # In a real test we'd need to mock it or have real services.
    
    executor = ToolExecutor(db_session, business_id=business.id, user_id=user.id, user_phone="1234567890", template_service=template_service)
    
    # We include line_items directly in the tool (as if LLM parsed them)
    from src.uimodels import LineItemInfo
    job_tool = AddJobTool(
        customer_name="Jane Doe",
        description="Fix gutters",
        line_items=[LineItemInfo(service_name="Gutter", description="Gutter Cleaning", quantity=1)]
    )
    
    result, _ = await executor.execute(job_tool)
    
    assert "Job added: Jane Doe" in result
    assert "Service    | Qty | Price | Total" in result
    assert "Gutter" in result
    assert "30.0" in result
