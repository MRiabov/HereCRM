import pytest
from src.services.integration_service import IntegrationService
from src.repositories import IntegrationRepository
from src.models import IntegrationType, Business

@pytest.fixture
def integration_service(async_session):
    repo = IntegrationRepository(async_session)
    return IntegrationService(repo)

@pytest.mark.asyncio
async def test_generate_api_key():
    key = IntegrationService.generate_api_key()
    assert key.startswith("sk_live_")
    assert len(key) > 40
    
    key2 = IntegrationService.generate_api_key()
    assert key != key2

@pytest.mark.asyncio
async def test_hash_key():
    key = "test_key"
    hashed = IntegrationService.hash_key(key)
    assert len(hashed) == 64  # SHA-256
    assert hashed == IntegrationService.hash_key(key)

@pytest.mark.asyncio
async def test_create_inbound_integration(async_session, integration_service):
    # Setup business
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    config, raw_key = await integration_service.create_inbound_integration(business.id, "Zapier")
    
    assert config.business_id == business.id
    assert config.label == "Zapier"
    assert config.type == IntegrationType.INBOUND_KEY
    assert raw_key.startswith("sk_live_")
    assert config.key_hash == IntegrationService.hash_key(raw_key)
    assert config.is_active is True

@pytest.mark.asyncio
async def test_validate_key(async_session, integration_service):
    # Setup business
    business = Business(name="Test Business")
    async_session.add(business)
    await async_session.flush()
    
    config, raw_key = await integration_service.create_inbound_integration(business.id, "Zapier")
    await async_session.commit()
    
    # Valid key (using a new session for clean check)
    found_config = await integration_service.validate_key(raw_key)
    assert found_config is not None
    assert found_config.id == config.id
    
    # Invalid key
    not_found = await integration_service.validate_key("sk_live_wrong")
    assert not_found is None
