import pytest
import os
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from src.models import Business
from sqlalchemy import select
from src.main import app
from src.database import get_db

@pytest.fixture
async def async_client(async_session):
    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

# Mock Stripe signature verification globally for this test file
@pytest.fixture
def mock_stripe_signature():
    with patch("stripe.Webhook.construct_event") as mock:
        yield mock

@pytest.fixture
def mock_load_config():
    with patch("src.services.billing_service.BillingService._load_config") as mock:
        yield mock

@pytest.mark.asyncio
async def test_stripe_webhook_checkout_completed(async_client, async_session, mock_stripe_signature, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    # Setup business
    business = Business(name="Test Business", subscription_status="free")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)
    
    # Payload
    payload = {
        "id": "evt_test_checkout",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "metadata": {
                    "business_id": str(business.id)
                }
            }
        }
    }
    
    # Mock event construction
    mock_event = MagicMock()
    mock_event.type = "checkout.session.completed"
    mock_event.data.object = payload["data"]["object"]
    mock_event.get = lambda k, d=None: payload.get(k, d)
    mock_stripe_signature.return_value = mock_event
    
    headers = {"stripe-signature": "t=123,v1=signature"}
    
    response = await async_client.post("/webhooks/stripe", json=payload, headers=headers)
    
    assert response.status_code == 200
    
    # Verify DB update
    await async_session.refresh(business)
    assert business.stripe_customer_id == "cus_test_123"
    assert business.stripe_subscription_id == "sub_test_123"
    assert business.subscription_status == "active"

@pytest.mark.asyncio
async def test_stripe_webhook_subscription_updated(async_client, async_session, mock_stripe_signature, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    
    business = Business(name="Test Business", stripe_customer_id="cus_test_123", subscription_status="active")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)
    
    # We rely on the billing config loaded from disk in BillingService
    payload = {
        "id": "evt_test_update",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test_123",
                "customer": "cus_test_123",
                "status": "active",
                "items": {
                    "data": [
                         {
                             "price": {"id": "price_1SrkGWEWj96BiJElrDXGNpyz"}, # Matches seat config
                             "quantity": 2
                         },
                         {
                             "price": {"id": "price_123_placeholder"}, # Matches employee_management config
                             "quantity": 1
                         }
                    ]
                },
                "metadata": {
                    "business_id": str(business.id)
                }
            }
        }
    }
    
    # Mock event
    mock_event = MagicMock()
    mock_event.type = "customer.subscription.updated"
    mock_event.data.object = payload["data"]["object"]
    mock_event.get = lambda k, d=None: payload.get(k, d)
    mock_stripe_signature.return_value = mock_event
    
    headers = {"stripe-signature": "t=123,v1=signature"}
    response = await async_client.post("/webhooks/stripe", json=payload, headers=headers)
    assert response.status_code == 200
    
    await async_session.refresh(business)
    
    # Logic: total_seats = 1 + quantity (2) = 3
    assert business.seat_limit == 3
    
    # Logic: active_addons = [addon_id for matched price] => ["employee_management"]
    assert "employee_management" in business.active_addons

@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature(async_client, mock_stripe_signature, monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    import stripe
    mock_stripe_signature.side_effect = stripe.error.SignatureVerificationError("Invalid sig", "sig_header", "secret")
    
    headers = {"stripe-signature": "invalid"}
    response = await async_client.post("/webhooks/stripe", json={}, headers=headers)
    
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"
