import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.database import Base
from src.models import Business, Job, User, JobCreationDefault
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool
from src.services.template_service import TemplateService
from datetime import datetime, timezone

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
async def test_execute_add_job_scheduled_today(
    test_session: AsyncSession, template_service: TemplateService
):
    # Setup business with SCHEDULED_TODAY preference
    biz = Business(name="Biz Scheduled Today", workflow_job_creation_default=JobCreationDefault.SCHEDULED_TODAY)
    test_session.add(biz)
    await test_session.flush()

    user = User(phone_number="999888777", business_id=biz.id, role="owner")
    test_session.add(user)
    await test_session.flush()

    from unittest.mock import MagicMock, patch, AsyncMock
    with patch("src.tool_executor.GeocodingService") as geo_mock:
        mock_instance = MagicMock()
        mock_instance.geocode = AsyncMock(return_value=(None, None, None, None, None, None, "123 Mock Lane"))
        geo_mock.return_value = mock_instance
        
        executor = ToolExecutor(test_session, biz.id, user.id, user.phone_number, template_service)
        
        tool = AddJobTool(
            customer_name="Scheduled Alice",
            description="Fix AC",
            price=200.0,
            location="123 Mock Lane"
        )

        result, metadata = await executor.execute(tool)

    assert "Job added: Scheduled Alice" in result
    assert metadata["action"] == "create"

    # Verify Job is scheduled for today
    from sqlalchemy import select
    res = await test_session.execute(select(Job))
    job = res.scalar_one()
    
    assert job.status == "SCHEDULED"
    assert job.scheduled_at is not None
    
    # Check if scheduled_at is close to now
    now = datetime.now(timezone.utc)
    diff = abs((job.scheduled_at.replace(tzinfo=timezone.utc) - now).total_seconds())
    assert diff < 60  # Should be within 1 minute
