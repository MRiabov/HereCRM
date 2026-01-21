import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, User, UserRole
from src.tool_executor import ToolExecutor
from src.uimodels import ManageEmployeesTool
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
async def test_scope_enforcement_blocked(test_session: AsyncSession, template_service: TemplateService):
    """Test that a basic business is blocked from premium tools."""
    # Ensure active_addons is initialized as empty list
    biz = Business(name="Free Biz", active_addons=[])
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="123", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, user.id, str(user.phone_number), template_service)
    
    # ManageEmployeesTool requires "manage_employees"
    tool = ManageEmployeesTool(action="list")
    
    result, metadata = await executor.execute(tool)
    
    # Expect blockage
    assert "Upgrade Required" in result
    assert "manage_employees" in result
    assert metadata is None

@pytest.mark.asyncio
async def test_scope_enforcement_allowed(test_session: AsyncSession, template_service: TemplateService):
    """Test that a business with the addon can access premium tools."""
    # Ensure active_addons contains the required scope
    biz = Business(name="Premium Biz", active_addons=["manage_employees"])
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="456", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, user.id, str(user.phone_number), template_service)
    
    tool = ManageEmployeesTool(action="list")
    
    result, metadata = await executor.execute(tool)
    
    # Expect success
    assert "Access granted to Employee Management: list" in result
    assert metadata is None

@pytest.mark.asyncio
async def test_scope_enforcement_default_allowed(test_session: AsyncSession, template_service: TemplateService):
    """Test that a new business gets all permissions by default (MVP)."""
    biz = Business(name="New Biz")
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="789", business_id=biz.id, role=UserRole.OWNER)
    test_session.add(user)
    await test_session.flush()

    executor = ToolExecutor(test_session, biz.id, user.id, str(user.phone_number), template_service)
    
    # Check ManageEmployeesTool
    res1, _ = await executor.execute(ManageEmployeesTool(action="list"))
    assert "Access granted to Employee Management" in res1

    # Check MassEmailTool
    from src.uimodels import MassEmailTool
    res2, _ = await executor.execute(MassEmailTool(subject="Hi", body="Dev"))
    assert "Access granted to Campaigns" in res2
