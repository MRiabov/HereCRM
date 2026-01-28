import pytest
import os
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch
from src.database import get_db, Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.models import User, Business

# In-memory DB for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(autouse=True)
async def clean_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_clerk_webhook_user_created():
    from src.main import app
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    
    with patch.dict(os.environ, {"CLERK_WEBHOOK_SECRET": "test_secret"}):
        with patch("src.api.webhooks.clerk.Webhook") as MockWebhook:
            instance = MockWebhook.return_value
            event_data = {
                "type": "user.created",
                "data": {
                    "id": "user_123",
                    "email_addresses": [{"email_address": "test@example.com"}],
                    "phone_numbers": [{"phone_number": "+1234567890"}],
                    "first_name": "John",
                    "last_name": "Doe"
                }
            }
            instance.verify.return_value = event_data
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/webhooks/clerk",
                    json=event_data,
                    headers={
                        "svix-id": "msg_123",
                        "svix-timestamp": "12345678",
                        "svix-signature": "sig_123"
                    }
                )
                
                assert response.status_code == 200
                assert response.json() == {"status": "success"}
                
                async with TestingSessionLocal() as session:
                    from src.repositories import UserRepository
                    user_repo = UserRepository(session)
                    user = await user_repo.get_by_clerk_id("user_123")
                    assert user is not None
                    assert user.email == "test@example.com"
                    assert user.name == "John Doe"

@pytest.mark.asyncio
async def test_clerk_webhook_org_created():
    from src.main import app
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    
    with patch.dict(os.environ, {"CLERK_WEBHOOK_SECRET": "test_secret"}):
        with patch("src.api.webhooks.clerk.Webhook") as MockWebhook:
            instance = MockWebhook.return_value
            event_data = {
                "type": "organization.created",
                "data": {
                    "id": "org_123",
                    "name": "Test Org"
                }
            }
            instance.verify.return_value = event_data
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/webhooks/clerk",
                    json=event_data,
                    headers={
                        "svix-id": "msg_123",
                        "svix-timestamp": "12345678",
                        "svix-signature": "sig_123"
                    }
                )
                
                assert response.status_code == 200
                
                async with TestingSessionLocal() as session:
                    from src.repositories import BusinessRepository
                    biz_repo = BusinessRepository(session)
                    biz = await biz_repo.get_by_clerk_id("org_123")
                    assert biz is not None
                    assert biz.name == "Test Org"

@pytest.mark.asyncio
async def test_clerk_webhook_membership_created():
    from src.main import app
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    
    # Pre-create user and business in the test DB
    async with TestingSessionLocal() as session:
        biz = Business(name="Old Name", clerk_org_id="org_membership_test")
        session.add(biz)
        await session.flush()
        user = User(name="John", clerk_id="user_membership_test", business_id=biz.id)
        session.add(user)
        await session.commit()

    with patch.dict(os.environ, {"CLERK_WEBHOOK_SECRET": "test_secret"}):
        with patch("src.api.webhooks.clerk.Webhook") as MockWebhook:
            instance = MockWebhook.return_value
            event_data = {
                "type": "organizationMembership.created",
                "data": {
                    "organization": {"id": "org_membership_test"},
                    "public_user_data": {"user_id": "user_membership_test"},
                    "role": "org:admin"
                }
            }
            instance.verify.return_value = event_data
            
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                response = await ac.post(
                    "/webhooks/clerk",
                    json=event_data,
                    headers={
                        "svix-id": "msg_123",
                        "svix-timestamp": "12345678",
                        "svix-signature": "sig_123"
                    }
                )
                
                assert response.status_code == 200
                
                async with TestingSessionLocal() as session:
                    from src.repositories import UserRepository
                    user_repo = UserRepository(session)
                    user = await user_repo.get_by_clerk_id("user_membership_test")
                    assert user.role == "owner"
                    assert user.business_id is not None
