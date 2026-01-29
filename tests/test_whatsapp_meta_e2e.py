import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db, Base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.uimodels import AddJobTool
from src.models import MessageType
from unittest.mock import AsyncMock, patch, ANY
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
async def setup_db():
    # Create tables
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Pre-create User
    phone = "16505551234"
    async with TestingSessionLocal() as db:
        from src.models import Business, User, UserRole
        biz = Business(name="Meta Review Biz")
        db.add(biz)
        await db.flush()
        user = User(phone_number=phone, business_id=biz.id, role=UserRole.OWNER)
        db.add(user)
        await db.commit()
    
    yield phone
    
    # Teardown
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_meta_webhook_format_e2e(setup_db):
    phone = setup_db
    secret = os.getenv("WHATSAPP_APP_SECRET", "dummy_secret")

    # Override get_db
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()

    # Payload matching Meta's official structure
    meta_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000",
                                "phone_number_id": "123456789"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Test User"},
                                    "wa_id": phone
                                }
                            ],
                            "messages": [
                                {
                                    "from": phone,
                                    "id": "wamid.HBgLMTY1MDU1NTEyMzQfAhIAEhgWM0VCMDY1RUVCOUM4ODlDMDVCOUMyNwA=",
                                    "timestamp": "1677610000",
                                    "text": {"body": "Add a job for John $100 fix leak"},
                                    "type": "text"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    # Patch dependencies
    with (
        patch("src.llm_client.parser.parse", new_callable=AsyncMock) as mock_parse,
        patch("src.services.messaging_service.MessagingService.send_message", new_callable=AsyncMock) as mock_send,
        patch("src.api.routes.template_service") as mock_template_service,
    ):
        # Mock LLM behavior
        mock_parse.return_value = AddJobTool(
            customer_name="John",
            price=100.0,
            description="fix leak",
        )

        # Mock template response
        mock_template_service.render.return_value = "Please confirm the job for John at $100."

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload_bytes = json.dumps(meta_payload).encode("utf-8")
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

            # 1. Verify response status
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["processed"] == 1

            # 2. Verify MessagingService was called to send the reply (Cloud API behavior)
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["recipient_phone"] == phone
            assert "confirm the job for John" in call_args.kwargs["content"]

@pytest.mark.asyncio
async def test_meta_webhook_image_handling(setup_db):
    phone = setup_db
    secret = os.getenv("WHATSAPP_APP_SECRET", "dummy_secret")
    app.dependency_overrides[get_db] = lambda: TestingSessionLocal()

    # Meta payload for an image message
    image_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1234567890",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": phone,
                                    "id": "wamid.IMAGE_ID",
                                    "timestamp": "1677610000",
                                    "type": "image",
                                    "image": {
                                        "caption": "Photo of the damage",
                                        "mime_type": "image/jpeg",
                                        "sha256": "sha_hash",
                                        "id": "meta_media_id"
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    with (
        patch("src.services.whatsapp_service.WhatsappService.handle_message", new_callable=AsyncMock) as mock_handle,
        patch("src.services.messaging_service.MessagingService.send_message", new_callable=AsyncMock) as mock_send,
    ):
        mock_handle.return_value = "Received your photo."

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload_bytes = json.dumps(image_payload).encode("utf-8")
            signature = hmac.new(
                secret.encode("utf-8"), payload_bytes, hashlib.sha256
            ).hexdigest()
            
            response = await ac.post(
                "/webhook",
                content=payload_bytes,
                headers={
                    "X-Hub-Signature-256": f"sha256={signature}",
                    "Content-Type": "application/json",
                },
            )

            assert response.status_code == 200
            mock_handle.assert_called_once()
            # Verify it recognized the image
            args = mock_handle.call_args
            assert args.kwargs["media_type"] == "image"
            
            # Verify reply sent
            mock_send.assert_called_with(
                recipient_phone=phone,
                content="Received your photo.",
                trigger_source=ANY,
                business_id=ANY
            )

@pytest.mark.asyncio
async def test_meta_webhook_verification(setup_db):
    """Test the GET challenge for Meta verification."""
    verify_token = "blue_cat_123" # From src/config/__init__.py default
    challenge = "1158201444"
    
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": verify_token,
                "hub.challenge": challenge
            }
        )
        assert response.status_code == 200
        assert response.text == challenge
