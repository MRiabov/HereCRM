import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, PipelineStage
from src.services.crm_service import CRMService
from src.tool_executor import ToolExecutor
from src.services.template_service import TemplateService
from src.uimodels import SearchTool, UpdateCustomerStageTool

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
async def test_customer_search_by_pipeline_stage(test_session: AsyncSession):
    biz = Business(name="Search Biz")
    test_session.add(biz)
    await test_session.flush()

    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.LOST)
    c2 = Customer(name="Bob", business_id=biz.id, pipeline_stage=PipelineStage.CONTACTED)
    test_session.add_all([c1, c2])
    await test_session.flush()

    from src.repositories import CustomerRepository
    repo = CustomerRepository(test_session)
    
    # Search for Lost
    results = await repo.search(query="all", business_id=biz.id, pipeline_stage="lost")
    assert len(results) == 1
    assert results[0].name == "Alice"

    # Search for Contacted
    results = await repo.search(query="all", business_id=biz.id, pipeline_stage="contacted")
    assert len(results) == 1
    assert results[0].name == "Bob"

@pytest.mark.asyncio
async def test_crm_service_update_stage(test_session: AsyncSession):
    biz = Business(name="Update Biz")
    test_session.add(biz)
    await test_session.flush()

    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    test_session.add(c1)
    await test_session.flush()

    service = CRMService(test_session, biz.id)
    updated = await service.update_customer_stage(c1.id, "lost")
    
    assert updated.pipeline_stage == PipelineStage.LOST
    
    # Verify persistence
    await test_session.refresh(c1)
    assert c1.pipeline_stage == PipelineStage.LOST

@pytest.mark.asyncio
async def test_tool_executor_search_with_stage(test_session: AsyncSession):
    biz = Business(name="Tool Search Biz")
    test_session.add(biz)
    await test_session.flush()

    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.LOST)
    test_session.add(c1)
    await test_session.flush()

    template_service = TemplateService()
    executor = ToolExecutor(test_session, biz.id, "123456", template_service)
    
    search_tool = SearchTool(query="Alice", pipeline_stage="lost", entity_type="customer")
    response, metadata = await executor.execute(search_tool)
    
    assert "Alice" in response
    assert "Not results Found" not in response # check for failure message typos if any

    search_tool_mismatch = SearchTool(query="Alice", pipeline_stage="contacted", entity_type="customer")
    response, metadata = await executor.execute(search_tool_mismatch)
    # The response for no results includes the query string, so we check for the lack of customer listing format
    assert "Alice (" not in response 
    assert "No results found" in response or "search_no_results" in response

@pytest.mark.asyncio
async def test_tool_executor_update_stage(test_session: AsyncSession):
    biz = Business(name="Tool Update Biz")
    test_session.add(biz)
    await test_session.flush()

    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    test_session.add(c1)
    await test_session.flush()

    template_service = TemplateService()
    executor = ToolExecutor(test_session, biz.id, "123456", template_service)
    
    update_tool = UpdateCustomerStageTool(query="Alice", stage="lost")
    response, metadata = await executor.execute(update_tool)
    
    assert "Updated Alice's stage to Lost" in response
    assert metadata["action"] == "update"
    assert metadata["new_stage"] == "lost"
    
    await test_session.refresh(c1)
    assert c1.pipeline_stage == PipelineStage.LOST
