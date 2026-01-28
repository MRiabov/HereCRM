import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db, Base
from src.models import LeadSource
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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
async def test_generic_webhook_email_onboarding():
    # Override get_db to use test session
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Initialize DB
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch LLMParser.parse singleton and TemplateService
    with (
        patch("src.llm_client.parser.parse", new_callable=AsyncMock) as mock_parse,
        patch("src.api.routes.template_service") as mock_template_service,
    ):
        mock_parse.return_value = "Mocked Response"
        mock_template_service.render.side_effect = lambda key, **kwargs: key

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            with patch("src.api.routes.settings.generic_webhook_secret", "test-secret"):
                # 1. New User via Email (Generic Webhook)
                email = "zapier_test@example.com"
                payload = {
                    "identity": email,
                    "message": "Hello from Zapier",
                    "source": LeadSource.ZAPIER
                }

                # Fail without header
                response = await ac.post("/webhooks/generic", json=payload)
                assert response.status_code == 401

                # Succeed with header
                response = await ac.post(
                    "/webhooks/generic", 
                    json=payload, 
                    headers={"X-API-Key": "test-secret"}
                )
                assert response.status_code == 200
            data = response.json()
            assert data["reply"] == "welcome_message"
            assert data["source"] == LeadSource.ZAPIER

            # Verify User created in DB
            async with TestingSessionLocal() as session:
                from src.repositories import UserRepository
                user_repo = UserRepository(session)
                user = await user_repo.get_by_email(email)
                assert user is not None
                assert user.email == email
                assert user.role == "OWNER"

@pytest.mark.asyncio
async def test_generic_webhook_existing_user_phone():
    # Override get_db to use test session
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Initialize DB and create a user
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    phone = "1234567890"
    async with TestingSessionLocal() as session:
        from src.models import User, Business
        biz = Business(name="Existing Biz")
        session.add(biz)
        await session.flush()
        user = User(phone_number=phone, business_id=biz.id, role="OWNER")
        session.add(user)
        await session.commit()

    # Patch LLMParser.parse singleton and TemplateService
    with (
        patch("src.llm_client.parser.parse", new_callable=AsyncMock) as mock_parse,
        patch("src.api.routes.template_service") as mock_template_service,
    ):
        mock_parse.return_value = "Processing command"
        mock_template_service.render.side_effect = lambda key, **kwargs: key

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            with patch("src.api.routes.settings.generic_webhook_secret", "test-secret"):
                payload = {
                    "identity": phone,
                    "message": "Status update",
                    "source": LeadSource.CRON
                }

                response = await ac.post(
                    "/webhooks/generic", 
                    json=payload,
                    headers={"X-API-Key": "test-secret"}
                )
                assert response.status_code == 200
                data = response.json()
            # User exists, so no welcome message, should return mock_parse value
            # Since handle_message returns reply which is 'welcome_back' or from parser
            # Actually _handle_idle returns 'welcome_back' if greeting, or parser response.
            # "Status update" is not a greeting, so it should be "Processing command"
            assert data["reply"] == "Processing command"
            assert data["source"] == LeadSource.CRON

@pytest.mark.asyncio
async def test_generic_webhook_rate_limit():
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    
    with (
        patch("src.api.routes.settings.generic_webhook_secret", "test-secret"),
        patch("src.api.routes.check_rate_limit") as mock_check,
    ):
        mock_check.return_value = True # Limit exceeded
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "identity": "limited@example.com",
                "message": "Hello",
                "source": "zapier"
            }

            response = await ac.post(
                "/webhooks/generic", 
                json=payload,
                headers={"X-API-Key": "test-secret"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "Too many requests" in data["reply"]
