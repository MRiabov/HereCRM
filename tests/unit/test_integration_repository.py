import pytest
import uuid
from src.repositories import IntegrationRepository
from src.models import IntegrationConfig, IntegrationType, Business

@pytest.mark.asyncio
async def test_integration_repository_crud(async_session):
    # Setup business
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    repo = IntegrationRepository(async_session)
    config = IntegrationConfig(
        business_id=business.id,
        type=IntegrationType.WEBHOOK,
        label="My Webhook",
        config_payload={"url": "https://example.com"}
    )
    repo.add(config)
    await async_session.commit()
    
    # Get by id
    found = await repo.get_by_id(config.id, business.id)
    assert found is not None
    assert found.label == "My Webhook"
    
    # Get active by type
    active_webhooks = await repo.get_active_by_type(business.id, IntegrationType.WEBHOOK)
    assert len(active_webhooks) == 1
    assert active_webhooks[0].id == config.id
    
    # Deactivate and check
    config.is_active = False
    await async_session.commit()
    active_now = await repo.get_active_by_type(business.id, IntegrationType.WEBHOOK)
    assert len(active_now) == 0

@pytest.mark.asyncio
async def test_get_by_key_hash(async_session):
    # Setup business
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    repo = IntegrationRepository(async_session)
    key_hash = "some_secret_hash"
    config = IntegrationConfig(
        business_id=business.id,
        type=IntegrationType.INBOUND_KEY,
        label="Zapier",
        key_hash=key_hash
    )
    repo.add(config)
    await async_session.commit()
    
    found = await repo.get_by_key_hash(key_hash)
    assert found is not None
    assert found.id == config.id
    assert found.business_id == business.id
