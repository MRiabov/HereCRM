import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, Service
from src.tool_executor import ToolExecutor
from src.uimodels import DeleteServiceTool, AddServiceTool
from src.services.template_service import TemplateService
from src.services.cache import ServiceCatalogCache

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

@pytest.fixture(autouse=True)
def clear_cache():
    ServiceCatalogCache.get_instance()._cache.clear()

@pytest.mark.asyncio
async def test_delete_service_exact_match(test_session, template_service):
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123", business_id=biz.id, role="owner")
    test_session.add(user)

    svc = Service(business_id=biz.id, name="Plumbing", default_price=100.0)
    test_session.add(svc)
    await test_session.commit()

    executor = ToolExecutor(test_session, biz.id, user.id, user.phone_number, template_service)

    # Exact match (case insensitive)
    tool = DeleteServiceTool(name="plumbing")
    result, metadata = await executor.execute(tool)

    assert "deleted" in result
    assert metadata["action"] == "delete"
    assert metadata["id"] == svc.id

    # Verify deletion
    remaining = await executor.service_repo.get_by_id(svc.id, biz.id)
    assert remaining is None

@pytest.mark.asyncio
async def test_delete_service_fuzzy_match(test_session, template_service):
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123", business_id=biz.id, role="owner")
    test_session.add(user)

    svc = Service(business_id=biz.id, name="Window Cleaning", default_price=50.0)
    test_session.add(svc)
    await test_session.commit()

    executor = ToolExecutor(test_session, biz.id, user.id, user.phone_number, template_service)

    # Fuzzy match "Window"
    tool = DeleteServiceTool(name="Window")
    result, metadata = await executor.execute(tool)

    assert "deleted" in result
    assert metadata["action"] == "delete"
    assert metadata["id"] == svc.id

    # Verify deletion
    remaining = await executor.service_repo.get_by_id(svc.id, biz.id)
    assert remaining is None

@pytest.mark.asyncio
async def test_delete_service_no_match(test_session, template_service):
    biz = Business(name="Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123", business_id=biz.id, role="owner")
    test_session.add(user)

    svc = Service(business_id=biz.id, name="Existing Service", default_price=50.0)
    test_session.add(svc)
    await test_session.commit()

    executor = ToolExecutor(test_session, biz.id, user.id, user.phone_number, template_service)

    tool = DeleteServiceTool(name="NonExistent")
    result, metadata = await executor.execute(tool)

    assert "Could not find service" in result
    assert metadata is None
