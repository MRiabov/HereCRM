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
        return service, mock_repo

@pytest.mark.asyncio
async def test_get_billing_status(billing_service):
    service, mock_repo = billing_service
    
    # Mock business data
    mock_business = MagicMock()
    mock_business.subscription_status = "active"
    mock_business.seat_limit = 5
    mock_business.active_addons = ["campaigns"]
    mock_business.stripe_customer_id = "cus_123"
    
    mock_repo.get_by_id_global.return_value = mock_business
    
    status = await service.get_billing_status(1)
    
    assert status["status"] == "active"
    assert status["seat_limit"] == 5
    assert "campaigns" in status["active_addons"]
    assert status["stripe_customer_id"] == "cus_123"

@pytest.mark.asyncio
async def test_create_checkout_session(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_business.stripe_customer_id = "cus_123"
    mock_repo.get_by_id_global.return_value = mock_business
    
    with patch("stripe.checkout.Session.create") as mock_stripe_create:
        mock_stripe_create.return_value = MagicMock(url="http://stripe.com/checkout")
        
        url = await service.create_checkout_session(
            1, "price_123", "http://success", "http://cancel"
        )
        
        assert url == "http://stripe.com/checkout"
        mock_stripe_create.assert_called_once()
        args, kwargs = mock_stripe_create.call_args
        assert kwargs["metadata"]["business_id"] == "1"
        assert kwargs["customer"] == "cus_123"

@pytest.mark.asyncio
async def test_create_upgrade_link_seat(billing_service):
    service, mock_repo = billing_service
    
    service.config = {
        "products": {
            "seat": {"price_id": "price_seat_123"}
        }
    }
    
    mock_business = MagicMock()
    mock_repo.get_by_id_global.return_value = mock_business
    
    with patch("stripe.checkout.Session.create") as mock_stripe_create:
        mock_stripe_create.return_value = MagicMock(url="http://stripe.com/checkout")
        
        result = await service.create_upgrade_link(1, "seat", None, "http://success", "http://cancel")
        
        assert result["url"] == "http://stripe.com/checkout"
        assert "Upgrade: Additional Seat" in result["description"]
        kwargs = mock_stripe_create.call_args[1]
        assert kwargs["line_items"][0]["price"] == "price_seat_123"

@pytest.mark.asyncio
async def test_create_upgrade_link_addon(billing_service):
    service, mock_repo = billing_service
    
    service.config = {
        "addons": [
            {"id": "campaign_messaging", "name": "Campaign Messaging", "price_id": "price_addon_456"}
        ]
    }
    
    mock_business = MagicMock()
    mock_repo.get_by_id_global.return_value = mock_business
    
    with patch("stripe.checkout.Session.create") as mock_stripe_create:
        mock_stripe_create.return_value = MagicMock(url="http://stripe.com/checkout")
        
        result = await service.create_upgrade_link(1, "addon", "campaign_messaging", "http://success", "http://cancel")
        
        assert result["url"] == "http://stripe.com/checkout"
        assert result["description"] == "Upgrade: Campaign Messaging"
        kwargs = mock_stripe_create.call_args[1]
        assert kwargs["line_items"][0]["price"] == "price_addon_456"

@pytest.mark.asyncio
async def test_get_billing_status_not_found(billing_service):
    service, mock_repo = billing_service
    mock_repo.get_by_id_global.return_value = None
    
    status = await service.get_billing_status(999)
    assert "error" in status
    assert status["error"] == "Business not found"

@pytest.mark.asyncio
async def test_create_checkout_session_stripe_error(billing_service):
    service, mock_repo = billing_service
    
    mock_business = MagicMock()
    mock_repo.get_by_id_global.return_value = mock_business
    
    with patch("stripe.checkout.Session.create") as mock_stripe_create:
        mock_stripe_create.side_effect = stripe.error.StripeError("API Error")
        
        with pytest.raises(stripe.error.StripeError):
            await service.create_checkout_session(1, "price_123", "http://success", "http://cancel")

@pytest.mark.asyncio
async def test_create_upgrade_link_invalid_item(billing_service):
    service, mock_repo = billing_service
    service.config = {"products": {}, "addons": []}
    
    mock_business = MagicMock()
    mock_repo.get_by_id_global.return_value = mock_business
    
    with pytest.raises(ValueError, match="Invalid item"):
        await service.create_upgrade_link(1, "invalid", "thing", "http://success", "http://cancel")
