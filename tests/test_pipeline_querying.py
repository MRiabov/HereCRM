import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, PipelineStage
from src.services.crm_service import CRMService

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
async def test_get_pipeline_summary(test_session: AsyncSession):
    biz = Business(name="Pipeline Biz")
    test_session.add(biz)
    await test_session.flush()

    # Add customers in different stages
    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    c2 = Customer(name="Bob", business_id=biz.id, pipeline_stage=PipelineStage.CONTACTED)
    c3 = Customer(name="Charlie", business_id=biz.id, pipeline_stage=PipelineStage.CONTACTED)
    c4 = Customer(name="David", business_id=biz.id, pipeline_stage=PipelineStage.CONVERTED_ONCE)
    test_session.add_all([c1, c2, c3, c4])
    await test_session.flush()

    service = CRMService(test_session, biz.id)
    summary = await service.get_pipeline_summary()

    assert summary[PipelineStage.NOT_CONTACTED.value]["count"] == 1
    assert "Alice" in summary[PipelineStage.NOT_CONTACTED.value]["examples"]
    assert summary[PipelineStage.CONTACTED.value]["count"] == 2
    assert "Bob" in summary[PipelineStage.CONTACTED.value]["examples"]
    assert "Charlie" in summary[PipelineStage.CONTACTED.value]["examples"]
    assert summary[PipelineStage.CONVERTED_ONCE.value]["count"] == 1
    assert "David" in summary[PipelineStage.CONVERTED_ONCE.value]["examples"]

@pytest.mark.asyncio
async def test_format_pipeline_summary(test_session: AsyncSession):
    biz = Business(name="Format Biz")
    test_session.add(biz)
    await test_session.flush()

    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    test_session.add(c1)
    await test_session.flush()

    service = CRMService(test_session, biz.id)
    report = await service.format_pipeline_summary()

    assert "### Pipeline Breakdown" in report
    assert "**Not Contacted**: 1 customer (Alice)" in report
    assert "**Contacted**: 0 customers" in report

@pytest.mark.asyncio
async def test_format_pipeline_summary_empty(test_session: AsyncSession):
    biz = Business(name="Empty Biz")
    test_session.add(biz)
    await test_session.flush()

    service = CRMService(test_session, biz.id)
    report = await service.format_pipeline_summary()

    assert "### Pipeline Breakdown" in report
    assert "**Not Contacted**: 0 customers" in report
