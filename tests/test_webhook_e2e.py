import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db, Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.uimodels import AddJobTool
from unittest.mock import AsyncMock, patch
import hmac
import hashlib
import json
import os

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
    # Ensure env var is set (should be by conftest, but explicit for clarity in this file logic if run standalone)
    secret = os.getenv("WHATSAPP_APP_SECRET", "dummy_secret")

    # Override get_db to use test session
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Initialize DB (fixture logic included here for simplicity in this flow)
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch LLMParser in routes
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

            # Serialize manually to ensure we sign the exact bytes
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(
                secret.encode("utf-8"), payload_bytes, hashlib.sha256
            ).hexdigest()
            sig_header = f"sha256={signature}"

            response = await ac.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": sig_header,
                    "Content-Type": "application/json",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "reply" in data
            assert "Please confirm" in data["reply"]

            # 2. Confirm
            payload_confirm = {"from_number": phone, "body": "Yes"}
            payload_confirm_bytes = json.dumps(payload_confirm).encode("utf-8")
            signature_confirm = hmac.new(
                secret.encode("utf-8"), payload_confirm_bytes, hashlib.sha256
            ).hexdigest()
            sig_confirm_header = f"sha256={signature_confirm}"

            response = await ac.post(
                "/webhook",
                content=payload_confirm_bytes,
                headers={
                    "X-Hub-Signature-256": sig_confirm_header,
                    "Content-Type": "application/json",
                },
            )
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
