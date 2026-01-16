import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.search_service import SearchService
from src.services.geocoding import GeocodingService
from src.uimodels import SearchTool
from src.models import Customer, Job, Request

@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def mock_geocoding_service():
    return MagicMock(spec=GeocodingService)

@pytest.fixture
def search_service(mock_session, mock_geocoding_service):
    service = SearchService(mock_session, mock_geocoding_service)
    # Mock the internal repositories
    service.customer_repo = AsyncMock()
    service.job_repo = AsyncMock()
    service.request_repo = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_search_service_instantiation():
    session = AsyncMock(spec=AsyncSession)
    geocoding_service = MagicMock(spec=GeocodingService)
    service = SearchService(session, geocoding_service)
    assert service.session == session
    assert service.geocoding_service == geocoding_service
    assert service.customer_repo is not None

@pytest.mark.asyncio
async def test_search_customers_delegation(search_service):
    # Setup
    search_service.customer_repo.search.return_value = [Customer(name="Test Customer")]
    params = SearchTool(query="Test", entity_type="customer")
    
    # Execute
    params.entity_type = "customer" # Ensure it is set
    result = await search_service.search(params, business_id=1)
    
    # Verify
    search_service.customer_repo.search.assert_awaited_once()
    call_args = search_service.customer_repo.search.await_args.kwargs
    assert call_args['query'] == "Test"
    assert call_args['business_id'] == 1
    assert "Test Customer" in result

@pytest.mark.asyncio
async def test_search_jobs_delegation(search_service):
    # Setup
    search_service.job_repo.search.return_value = [Job(description="Fix Sink")]
    params = SearchTool(query="Sink", entity_type="job")
    
    # Execute
    result = await search_service.search(params, business_id=1)
    
    # Verify
    search_service.job_repo.search.assert_awaited_once()
    assert "Fix Sink" in result

@pytest.mark.asyncio
async def test_search_requests_delegation(search_service):
    # Setup
    search_service.request_repo.search.return_value = [Request(content="Need help")]
    params = SearchTool(query="help", entity_type="request")
    
    # Execute
    result = await search_service.search(params, business_id=1)
    
    # Verify
    search_service.request_repo.search.assert_awaited_once()
    assert "Need help" in result

@pytest.mark.asyncio
async def test_search_aggregation_all(search_service):
    # Setup
    search_service.customer_repo.search.return_value = [Customer(name="C1")]
    search_service.job_repo.search.return_value = [Job(description="J1")]
    search_service.request_repo.search.return_value = [Request(content="R1")]
    params = SearchTool(query="all") # entity_type is None
    
    # Execute
    result = await search_service.search(params, business_id=1)
    
    # Verify all repos called
    search_service.customer_repo.search.assert_awaited_once()
    search_service.job_repo.search.assert_awaited_once()
    search_service.request_repo.search.assert_awaited_once()
    
    assert "C1" in result
    assert "J1" in result
    assert "R1" in result

@pytest.mark.asyncio
async def test_search_routing_customer(search_service):
    params = SearchTool(query="test", entity_type="customer")
    await search_service.search(params, business_id=1)
    
    search_service.customer_repo.search.assert_awaited_once()
    search_service.job_repo.search.assert_not_awaited()
    search_service.request_repo.search.assert_not_awaited()

@pytest.mark.asyncio
async def test_search_routing_lead(search_service):
    # Lead routes to customer repo logic
    params = SearchTool(query="test", entity_type="lead")
    await search_service.search(params, business_id=1)
    
    search_service.customer_repo.search.assert_awaited_once()
    
@pytest.mark.asyncio
async def test_date_parsing(search_service):
    params = SearchTool(
        query="test", 
        entity_type="request",
        min_date="2023-01-01T00:00:00",
        max_date="2023-12-31T23:59:59"
    )
    search_service.request_repo.search.return_value = []
    
    await search_service.search(params, business_id=1)
    
    call_args = search_service.request_repo.search.await_args.kwargs
    assert call_args['min_date'].year == 2023
    assert call_args['max_date'].year == 2023
