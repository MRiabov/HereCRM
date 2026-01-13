import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db, Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.uimodels import AddJobTool
from unittest.mock import AsyncMock, patch

# In-memory DB for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture
async def db_session():
    # Create tables
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    # Teardown
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_webhook_e2e():
    # Override get_db to use test session
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Initialize DB (fixture logic included here for simplicity in this flow)
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch LLMParser in routes
    # We define behavior: First call returns AddJobTool, Second call (implied by flow) irrelevant as "Yes" is handled by code not LLM usually
    # But wait, "Yes" is handled by _handle_waiting_confirm which does NOT call LLM.
    # So we just need to patch it for the first call.
    with patch("src.api.routes.LLMParser") as MockParserInfo:
        mock_instance = MockParserInfo.return_value
        mock_instance.parse = AsyncMock(
            return_value=AddJobTool(
                customer_name="Alice", description="Fix sink", price=100.0
            )
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Send "Add Job..." from NEW phone (triggers Onboarding)
            phone = "999888777"
            payload = {"from_number": phone, "body": "Add job for Alice fix sink 100"}

            response = await ac.post("/webhook", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "Please confirm" in data["reply"]

            # 2. Confirm
            payload_confirm = {"from_number": phone, "body": "Yes"}
            response = await ac.post("/webhook", json=payload_confirm)
            assert response.status_code == 200
            data = response.json()
            assert "Job added" in data["reply"]

            # 3. Verify DB
            async with TestingSessionLocal() as session:
                from src.repositories import (
                    UserRepository,
                    JobRepository,
                    BusinessRepository,
                )

                # Check User and Business created
                user_repo = UserRepository(session)
                user = await user_repo.get_by_phone(phone)
                assert user is not None
                assert user.role == "owner"

                # Check Business
                biz_repo = BusinessRepository(session)
                biz = await biz_repo.get_by_id_global(user.business_id)
                assert biz is not None
                assert "999888777" in biz.name

                # Check Job created
                job_repo = JobRepository(session)
                jobs = await job_repo.search("sink", user.business_id)
                assert len(jobs) == 1
                assert jobs[0].description == "Fix sink"
                assert (
                    jobs[0].customer_id is not None
                )  # Logic should have created customer too?
                # AddJobTool logic in ToolExecutor (WP03) usually creates customer if needed.
