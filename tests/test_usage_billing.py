import pytest
import stripe
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
                "messaging": {"price_id": "price_msg_123"}
            }
        }
        return service, mock_repo

@pytest.mark.asyncio
async def test_track_message_sent(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_business.message_count_current_period = 10
    mock_business.stripe_subscription_id = "sub_123"
    mock_repo.get_by_id_global.return_value = mock_business
    
    with patch("stripe.Subscription.retrieve") as mock_retrieve, \
         patch("stripe.SubscriptionItem.create_usage_record", create=True) as mock_usage:
        
        mock_retrieve.return_value = {
            "items": {
                "data": [
                    {"id": "si_123", "price": {"id": "price_msg_123"}}
                ]
            }
        }
        
        await service.track_message_sent(1)
        
        assert mock_business.message_count_current_period == 11
        mock_usage.assert_called_once_with(
            "si_123",
            quantity=1,
            action="increment"
        )
        service.session.commit.assert_called()

@pytest.mark.asyncio
async def test_get_billing_status_with_usage(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_business.subscription_status = "active"
    mock_business.message_count_current_period = 1050
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
    
    service.session.execute = AsyncMock()
    service.session.execute.return_value.scalar_one_or_none = AsyncMock(return_value=mock_business)
    
    await service.process_webhook({
        "type": "invoice.created",
        "data": {"object": {"customer": "cus_123"}}
    })
    
    assert mock_business.message_count_current_period == 0
    assert mock_business.billing_cycle_anchor is not None
    service.session.commit.assert_called()
