import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.tool_executor import ToolExecutor
from src.uimodels import AddJobTool
from src.models import Business, UserRole

@pytest.mark.asyncio
async def test_tool_executor_add_job_safeguard_blocked():
    session = AsyncMock()
    template_service = MagicMock()
    
    # Mock user preferences with safeguard enabled
    user = MagicMock()
    user.id = 1
    user.role = UserRole.OWNER
    user.preferences = {
        "default_city": "Dublin",
        "default_country": "Ireland",
        "geocoding_safeguard_enabled": True,
        "geocoding_max_distance_km": 100.0
    }
    
    business = MagicMock(spec=Business)
    business.id = 1
    business.workflow_invoicing = "manual"
    business.workflow_quoting = "manual"
    business.active_addons = []
    
    executor = ToolExecutor(session, business_id=1, user_id=1, user_phone="+353871234567", template_service=template_service)
    
    # Mock repositories
    executor.user_repo = AsyncMock()
    executor.user_repo.get_by_id.return_value = user
    executor.customer_repo = AsyncMock()
    executor.customer_repo.get_by_name.return_value = None
    executor.customer_repo.get_by_phone.return_value = None
    
    # Mock business fetch
    session.get.return_value = business
    
    # Mock GeocodingService.geocode to return None (as if blocked)
    executor.geocoding_service = AsyncMock()
    executor.geocoding_service.geocode.return_value = (None, None, None, None, None, None, "London")
    
    tool = AddJobTool(
        customer_name="John Doe",
        location="London", # Far from Dublin
        description="Clean windows"
    )
    
    result, metadata = await executor._execute_add_job(tool)
    
    assert "too far from your default city" in result
    assert metadata is None

@pytest.mark.asyncio
async def test_tool_executor_add_job_safeguard_allowed():
    session = AsyncMock()
    template_service = MagicMock()
    
    # Mock user preferences with safeguard enabled
    user = MagicMock()
    user.id = 1
    user.role = UserRole.OWNER
    user.preferences = {
        "default_city": "Dublin",
        "default_country": "Ireland",
        "geocoding_safeguard_enabled": True,
        "geocoding_max_distance_km": 100.0
    }
    
    business = MagicMock(spec=Business)
    business.id = 1
    business.workflow_invoicing = "manual"
    business.workflow_quoting = "manual"
    business.active_addons = []
    
    executor = ToolExecutor(session, business_id=1, user_id=1, user_phone="+353871234567", template_service=template_service)
    
    # Mock repositories
    executor.user_repo = AsyncMock()
    executor.user_repo.get_by_id.return_value = user
    executor.customer_repo = AsyncMock()
    executor.customer_repo.get_by_name.return_value = None
    executor.customer_repo.get_by_phone.return_value = None
    
    # Mock business fetch
    session.get.return_value = business
    
    # Mock GeocodingService.geocode to return valid coords
    executor.geocoding_service = AsyncMock()
    executor.geocoding_service.geocode.return_value = (53.3, -6.2, "Main St", "Dublin", "Ireland", "D1", "Main St, Dublin")
    
    # Mock WorkflowSettingsService
    executor.workflow_service = AsyncMock()
    executor.workflow_service.get_settings.return_value = {
        "workflow_job_creation_default": "unscheduled"
    }
    
    # Mock CRMService to avoid real DB calls for job creation
    with patch("src.tool_executor.CRMService") as mock_crm:
        mock_crm_instance = mock_crm.return_value
        mock_crm_instance.create_job = AsyncMock()
        mock_crm_instance.create_job.return_value = MagicMock(id=123, value=100.0, customer=MagicMock(name="John Doe"), location="Main St, Dublin", description="Clean windows")
        
        template_service.render.return_value = "Job Added Summary"
        
        tool = AddJobTool(
            customer_name="John Doe",
            location="Main St",
            description="Clean windows"
        )
        
        result, metadata = await executor._execute_add_job(tool)
        
        assert "Job Added Summary" in result
        assert metadata["action"] == "create"
        assert metadata["id"] == 123
