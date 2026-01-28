import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.billing_service import BillingService

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def billing_service(mock_session):
    with patch("src.services.billing_service.BusinessRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_by_id_global = AsyncMock()
        service = BillingService(mock_session)
        service.business_repo = mock_repo
        service.config = {
            "products": {
                "messaging": {
                    "price_id": "price_msg_123",
                    "free_limit": 1000,
                    "overage_rate": 0.02
                }
            }
        }
        return service, mock_repo

@pytest.mark.asyncio
async def test_track_message_sent(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_business.message_count_current_period = 10
    mock_business.message_credits = 0
    mock_business.stripe_subscription_id = "sub_123"
    mock_repo.get_by_id_global.return_value = mock_business
    
    with patch("stripe.Subscription.retrieve") as mock_retrieve, \
         patch("httpx.AsyncClient") as mock_client_cls:
        
        mock_retrieve.return_value = {
            "items": {
                "data": [
                    {"id": "si_123", "price": {"id": "price_msg_123"}}
                ]
            }
        }
        
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(raise_for_status=MagicMock())
        
        mock_instance = mock_client_cls.return_value
        mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        await service.track_message_sent(1)
        
        assert mock_business.message_count_current_period == 11
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["data"]["quantity"] == "1"
        assert kwargs["data"]["action"] == "increment"
        service.session.commit.assert_called()

@pytest.mark.asyncio
async def test_get_billing_status_with_usage(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_business.subscription_status = "active"
    mock_business.message_count_current_period = 1050
    mock_business.message_credits = -50
    mock_business.stripe_customer_id = "cus_123"
    mock_business.seat_limit = 1
    mock_business.active_addons = []
    mock_repo.get_by_id_global.return_value = mock_business
    
    status = await service.get_billing_status(1)
    
    assert status["usage"]["messages"] == 1050
    assert status["usage"]["overage"] == 50
    assert status["usage"]["estimated_cost"] == pytest.approx(50 * 0.02)

@pytest.mark.asyncio
async def test_handle_invoice_created_resets_count(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_business.id = 1
    mock_business.message_count_current_period = 500
    
    # Mock session.execute to return a result that has scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_business
    service.session.execute = AsyncMock(return_value=mock_result)
    
    await service.process_webhook({
        "type": "invoice.created",
        "data": {"object": {"customer": "cus_123"}}
    })
    
    assert mock_business.message_count_current_period == 0
    assert mock_business.billing_cycle_anchor is not None
    service.session.commit.assert_called()
