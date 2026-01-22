import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.config import settings
from src.utils.security import Signer
from src.services.integration_service import IntegrationService
from src.repositories import IntegrationRepository
from src.models import Business
from src.database import get_db

@pytest.fixture
def client():
    # Use TestClient with a fresh instance or the global app
    return TestClient(app)

@pytest.mark.asyncio
async def test_provisioning_flow(client, async_session):
    """Test the provisioning endpoint with signature verification."""
    # Override DB
    app.dependency_overrides[get_db] = lambda: async_session
    
    try:
        # 1. Prepare valid signature
        config_type = "INBOUND_KEY"
        label = "Zapier Primary"
        # We sign the same string as the server expects
        auth_id = Signer.sign(config_type + label, settings.secret_key)
        
        # 2. Call provisioning
        payload = {
            "auth_id": auth_id,
            "config_type": config_type,
            "label": label,
            "payload": {"business_id": 1, "owner": "John"}
        }
        
        response = client.post("/api/v1/integrations/provision", json=payload)
        assert response.status_code == 201
        assert "config_id" in response.json()

        # 3. Invalid signature
        payload["auth_id"] = "wrong_signature"
        response = client.post("/api/v1/integrations/provision", json=payload)
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_leads_ingestion_api_key(client, async_session):
    """Test lead ingestion with API Key authentication."""
    # Setup: Create business and API Key
    biz = Business(name="Test Biz")
    async_session.add(biz)
    await async_session.commit()
    await async_session.refresh(biz)
    
    # Use real service to generate key and hash
    service = IntegrationService(IntegrationRepository(async_session))
    config, raw_key = await service.create_inbound_integration(biz.id, "Test Key")
    await async_session.commit()
    
    # Override get_db to use our async_session
    app.dependency_overrides[get_db] = lambda: async_session
    
    try:
        # 1. Valid API Key
        headers = {"X-API-Key": raw_key}
        payload = {
            "name": "New Lead",
            "phone": "353899485670",
            "email": "lead@example.com",
            "source": "fb_ads"
        }
        
        response = client.post("/api/v1/integrations/leads", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "customer_id" in data
        assert not data["is_existing"]

        # 2. Invalid API Key
        headers = {"X-API-Key": "invalid_key"}
        response = client.post("/api/v1/integrations/leads", json=payload, headers=headers)
        assert response.status_code == 401

        # 3. Missing API Key
        response = client.post("/api/v1/integrations/leads", json=payload)
        # FastAPI returns 422 if required Header is missing
        assert response.status_code == 422
        
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_requests_ingestion(client, async_session):
    """Test service request ingestion."""
    biz = Business(name="Test Biz")
    async_session.add(biz)
    await async_session.commit()
    await async_session.refresh(biz)
    
    service = IntegrationService(IntegrationRepository(async_session))
    config, raw_key = await service.create_inbound_integration(biz.id, "Test Key")
    await async_session.commit()

    app.dependency_overrides[get_db] = lambda: async_session
    
    try:
        headers = {"X-API-Key": raw_key}
        payload = {
            "name": "Service Lead",
            "phone": "3531234567",
            "address": "123 Dublin St",
            "service_type": "Repair",
            "notes": "Leaking pipe"
        }
        
        response = client.post("/api/v1/integrations/requests", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert "request_id" in data
        assert "customer_id" in data

    finally:
        app.dependency_overrides.clear()
