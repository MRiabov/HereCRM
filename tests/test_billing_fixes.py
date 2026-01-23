import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.tool_executor import ToolExecutor, GetBillingStatusTool, RequestUpgradeTool
from src.services.billing_service import BillingService
from src.uimodels import RequestUpgradeTool
from src.models import Business, User, UserRole

@pytest.mark.asyncio
async def test_upgrade_messaging_allowed():
    """Verify that 'messaging' is a valid item_type for RequestUpgradeTool."""
    # This should not raise validation error
    tool = RequestUpgradeTool(item_type="messaging", quantity=1000)
    assert tool.item_type == "messaging"

@pytest.mark.asyncio
async def test_billing_service_creates_messaging_link():
    """Verify BillingService handles messaging upgrade type."""
    mock_session = AsyncMock()
    service = BillingService(mock_session)
    
    # Mock config
    service.config = {
        "products": {
            "messaging": {
                "name": "Messaging Pack",
                "price_id": "price_test_123",
                "overage_rate": 0.02
            },
             "seat": {
                "name": "Seat",
                "price_id": "price_seat_123"
            }
        },
        "addons": []
    }
    
    # Mock business repo
    mock_business = MagicMock(spec=Business)
    mock_business.stripe_customer_id = "cus_123"
    service.business_repo.get_by_id_global = AsyncMock(return_value=mock_business)
    
    # Mock stripe session create
    with patch("stripe.checkout.Session.create", return_value=MagicMock(url="http://checkout.url")) as mock_create:
        result = await service.create_upgrade_link(
            business_id=1,
            item_type="messaging",
            item_id=None,
            success_url="http://succ",
            cancel_url="http://canc"
        )
        
        assert result["url"] == "http://checkout.url"
        assert result["description"] == "Upgrade: Messaging Pack"
        
        # Verify call args used correct price_id
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["line_items"][0]["price"] == "price_test_123"

@pytest.mark.asyncio
async def test_tool_executor_shows_messaging_option():
    """Verify ToolExecutor displays messaging upgrade option."""
    mock_session = AsyncMock()
    
    # Setup mocks
    executor = ToolExecutor(mock_session, 1, 1, "123", MagicMock())
    executor.billing_service = AsyncMock(spec=BillingService)
    # Mock the config attribute access on billing service mock
    executor.billing_service.config = {
        "products": {
            "messaging": {
                "name": "Messaging Test",
                "overage_rate": 0.05
            }
        },
        "addons": []
    }
    
    # Mock get_billing_status return
    executor.billing_service.get_billing_status.return_value = {
        "status": "active",
        "seat_limit": 5,
        "active_addons": [],
        "usage": {"messages": 1500, "credits": 500, "estimated_cost": 0.0}
    }
    
    executor.user_repo.get_team_members = AsyncMock(return_value=[])
    
    # Run
    await executor._execute_get_billing_status(GetBillingStatusTool())
    
    # Assert
    # We check if template_service.render was called with the correct available_upgrades string
    calls = executor.template_service.render.call_args_list
    
    # Find the call for "billing_status_body"
    body_call = None
    for call in calls:
        if call[0][0] == "billing_status_body":
            body_call = call
            break
            
    assert body_call is not None
    # Check that free_limit correctly displays credits
    assert body_call[1]["free_limit"] == "500 credits remaining"
    
    available_upgrades = body_call[1]["available_upgrades"]
    assert "- Messaging Test (€0.05/msg overage or buy pack)" in available_upgrades
