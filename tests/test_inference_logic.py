import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, Service
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool, LineItemInfo
from src.services.template_service import TemplateService
from src.services.inference_service import InferenceService

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
async def test_inference_logic_with_catalog(test_session: AsyncSession):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    # Add a service to the catalog
    svc = Service(
        business_id=biz.id,
        name="Window Clean",
        default_price=50.0,
        description="Standard window cleaning"
    )
    test_session.add(svc)
    await test_session.flush()

    inference_service = InferenceService(test_session)

    # 1. Test inference by total_price
    raw_items = [LineItemInfo(description="Window Clean", total_price=100.0)]
    inferred = await inference_service.infer_line_items(biz.id, raw_items)
    
    assert len(inferred) == 1
    assert inferred[0].service_id == svc.id
    assert inferred[0].quantity == 2.0
    assert inferred[0].unit_price == 50.0
    assert inferred[0].total_price == 100.0

    # 2. Test inference by quantity
    raw_items = [LineItemInfo(description="window", quantity=3.0)]
    inferred = await inference_service.infer_line_items(biz.id, raw_items)
    
    assert len(inferred) == 1
    assert inferred[0].service_id == svc.id
    assert inferred[0].quantity == 3.0
    assert inferred[0].unit_price == 50.0
    assert inferred[0].total_price == 150.0


@pytest.mark.asyncio
async def test_tool_executor_with_line_items(
    test_session: AsyncSession, template_service: TemplateService
):
    biz = Business(name="Test Biz")
    test_session.add(biz)
    await test_session.flush()

    svc = Service(
        business_id=biz.id,
        name="Gutter Clean",
        default_price=40.0
    )
    test_session.add(svc)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, "123456789", template_service)
    
    tool = AddJobTool(
        customer_name="Alice",
        line_items=[
            LineItemInfo(description="Gutter Clean", quantity=2.0),
            LineItemInfo(description="Random Repair", total_price=30.0)
        ]
    )

    result, metadata = await executor.execute(tool)
    
    # Verify Job and Line Items in DB
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload

    stmt = select(Job).options(joinedload(Job.line_items)).where(Job.id == metadata["id"])
    res = await test_session.execute(stmt)
    job = res.unique().scalar_one()

    assert len(job.line_items) == 2
    
    # Check Gutter Clean (Catalog match)
    gutter_item = next(li for li in job.line_items if "Gutter" in li.description)
    assert gutter_item.service_id == svc.id
    assert gutter_item.quantity == 2.0
    assert gutter_item.unit_price == 40.0
    assert gutter_item.total_price == 80.0

    # Check Random Repair (Ad-hoc)
    repair_item = next(li for li in job.line_items if "Repair" in li.description)
    assert repair_item.service_id is None
    assert repair_item.total_price == 30.0

    # Check Job total value (updated by event listener)
    # Wait, in SQLite memory with flush, the listener should have run.
    assert job.value == 110.0
