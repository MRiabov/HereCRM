import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.search_service import SearchService
from src.services.geocoding import GeocodingService
from src.uimodels import SearchTool

@pytest.mark.asyncio
async def test_search_service_instantiation():
    session = AsyncMock(spec=AsyncSession)
    geocoding_service = MagicMock(spec=GeocodingService)
    
    service = SearchService(session, geocoding_service)
    
    assert service.session == session
    assert service.geocoding_service == geocoding_service
    assert service.customer_repo is not None
    assert service.job_repo is not None
    assert service.request_repo is not None

def test_search_tool_detailed_flag():
    # Test setting explicit True
    tool = SearchTool(query="test", detailed=True)
    assert tool.detailed is True
    assert tool.query == "test"
    
    # Test default value
    tool_default = SearchTool(query="test")
    assert tool_default.detailed is False
