import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Customer, PipelineStage
from src.repositories import CustomerRepository

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
async def test_search_filter_pipeline_stage(test_session):
    """Test filtering customers by exact pipeline stage."""
    biz = Business(name="Search Biz")
    test_session.add(biz)
    await test_session.commit()

    # Create customers in different stages
    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    c2 = Customer(name="Bob", business_id=biz.id, pipeline_stage=PipelineStage.CONTACTED)
    c3 = Customer(name="Charlie", business_id=biz.id, pipeline_stage=PipelineStage.CONVERTED_ONCE)
    c4 = Customer(name="Dave", business_id=biz.id, pipeline_stage=PipelineStage.LOST)
    
    test_session.add_all([c1, c2, c3, c4])
    await test_session.commit()
    
    repo = CustomerRepository(test_session)
    
    # 1. Search for LOST
    results_lost = await repo.search(query="all", business_id=biz.id, pipeline_stage="lost")
    assert len(results_lost) == 1
    assert results_lost[0].name == "Dave"
    
    # 2. Search for NOT_CONTACTED
    results_nc = await repo.search(query="all", business_id=biz.id, pipeline_stage="not_contacted")
    assert len(results_nc) == 1
    assert results_nc[0].name == "Alice"
    
    # 3. Search for CONVERTED_ONCE
    results_co = await repo.search(query="all", business_id=biz.id, pipeline_stage="converted_once")
    assert len(results_co) == 1
    assert results_co[0].name == "Charlie"
    
    # 4. Search with Name + Stage
    # "Bob" in Contacted -> Should find Bob
    results_bob = await repo.search(query="Bob", business_id=biz.id, pipeline_stage="contacted")
    assert len(results_bob) == 1
    assert results_bob[0].name == "Bob"
    
    # "Bob" in Lost -> Should find NOBODY
    results_bob_lost = await repo.search(query="Bob", business_id=biz.id, pipeline_stage="lost")
    assert len(results_bob_lost) == 0

@pytest.mark.asyncio
async def test_search_pipeline_defaults(test_session):
    """Ensure standard searches don't filter by stage unless requested."""
    biz = Business(name="Def Biz")
    test_session.add(biz)
    await test_session.commit()
    
    c1 = Customer(name="Alice", business_id=biz.id, pipeline_stage=PipelineStage.LOST)
    c2 = Customer(name="Bob", business_id=biz.id, pipeline_stage=PipelineStage.NOT_CONTACTED)
    test_session.add_all([c1, c2])
    await test_session.commit()
    
    repo = CustomerRepository(test_session)
    
    results = await repo.search(query="all", business_id=biz.id)
    assert len(results) == 2
