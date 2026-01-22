import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from src.handlers.integration_handlers import IntegrationEventHandler
from src.models.integration_config import IntegrationConfig, IntegrationType

@pytest.mark.asyncio
async def test_handle_job_booked_dispatches_webhook():
    # Setup test data
    data = {
        "job_id": 1,
        "business_id": 100,
        "value": 250.0
    }
    
    # Mocking DB response for integrations
    mock_config = MagicMock(spec=IntegrationConfig)
    mock_config.id = "webhook-uuid"
    mock_config.config_payload = {
        "url": "https://webhook.site/test",
        "signing_secret": "test-secret"
    }
    
    # Mock repositories
    with patch("src.handlers.integration_handlers.IntegrationRepository") as MockIntegrationRepo, \
         patch("src.handlers.integration_handlers.JobRepository") as MockJobRepo, \
         patch("src.handlers.integration_handlers.AsyncSessionLocal") as MockSession:
        
        # Setup Job mock
        mock_job = MagicMock()
        mock_job.id = 1
        mock_job.description = "Test Job"
        mock_job.value = 250.0
        mock_job.scheduled_at = datetime(2026, 1, 22, 12, 0, tzinfo=timezone.utc)
        mock_job.location = "123 Test St"
        
        mock_item = MagicMock()
        mock_item.description = "Line Item 1"
        mock_item.quantity = 1
        mock_item.unit_price = 250.0
        mock_item.total_price = 250.0
        mock_job.line_items = [mock_item]
        
        mock_customer = MagicMock()
        mock_customer.id = 50
        mock_customer.name = "Test Customer"
        mock_customer.phone = "123456789"
        mock_job.customer = mock_customer
        
        # Setup repo method returns
        instance_int = MockIntegrationRepo.return_value
        instance_int.get_active_by_type = AsyncMock(return_value=[mock_config])
        
        instance_job = MockJobRepo.return_value
        instance_job.get_with_line_items = AsyncMock(return_value=mock_job)
        
        # Mock httpx
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "OK"
            mock_post.return_value = mock_response
            
            # Execute handler
            await IntegrationEventHandler.handle_job_booked(data)
            
            # Assertions
            instance_int.get_active_by_type.assert_called_once_with(100, IntegrationType.WEBHOOK)
            instance_job.get_with_line_items.assert_called_once_with(1, 100)
            
            # Verify HTTP call
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "https://webhook.site/test"
            assert "X-HereCRM-Signature" in kwargs["headers"]
            
            # Verify payload contains expected data
            import json
            payload = json.loads(kwargs["content"])
            assert payload["event"] == "job.booked"
            assert payload["job"]["id"] == 1
            assert payload["customer"]["name"] == "Test Customer"
            assert len(payload["line_items"]) == 1

@pytest.mark.asyncio
async def test_handle_job_booked_no_integrations():
    data = {"job_id": 1, "business_id": 100}
    
    with patch("src.handlers.integration_handlers.IntegrationRepository") as MockIntegrationRepo, \
         patch("src.handlers.integration_handlers.JobRepository") as MockJobRepo, \
         patch("src.handlers.integration_handlers.AsyncSessionLocal"):
        
        instance_int = MockIntegrationRepo.return_value
        instance_int.get_active_by_type = AsyncMock(return_value=[])
        
        instance_job = MockJobRepo.return_value
        instance_job.get_with_line_items = AsyncMock(return_value=MagicMock())
        
        with patch("httpx.AsyncClient.post") as mock_post:
            await IntegrationEventHandler.handle_job_booked(data)
            mock_post.assert_not_called()
