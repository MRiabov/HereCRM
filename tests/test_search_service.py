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
    result, data = await search_service.search(params, business_id=1)
    
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
    result, data = await search_service.search(params, business_id=1)
    
    # Verify
    search_service.job_repo.search.assert_awaited_once()
    assert "Fix Sink" in result

@pytest.mark.asyncio
async def test_search_requests_delegation(search_service):
    # Setup
    search_service.request_repo.search.return_value = [Request(description="Need help")]
    params = SearchTool(query="help", entity_type="request")
    
    # Execute
    result, data = await search_service.search(params, business_id=1)

    
    # Verify
    search_service.request_repo.search.assert_awaited_once()
    assert "Need help" in result

@pytest.mark.asyncio
async def test_search_aggregation_all(search_service):
    # Setup
    search_service.customer_repo.search.return_value = [Customer(name="C1")]
    search_service.job_repo.search.return_value = [Job(description="J1")]
    search_service.request_repo.search.return_value = [Request(description="R1")]
    params = SearchTool(query="all") # entity_type is None
    
    # Execute
    result, data = await search_service.search(params, business_id=1)
    
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

@pytest.mark.asyncio
async def test_search_formatting_detailed(search_service):
    # Setup Customer with full details
    c = Customer(
        name="John Doe", 
        phone="123", 
        street="Main St", 
        city="Dublin", 
        details="VIP"
    )
    search_service.customer_repo.search.return_value = [c]
    
    # Test Detailed
    params = SearchTool(query="John", entity_type="customer", detailed=True)
    result, data = await search_service.search(params, business_id=1)
    
    assert "John Doe (123)" in result
    assert "Main St" in result
    assert "Dublin" in result
    assert "VIP" in result

    # Test Concise (Default)
    params.detailed = False
    result_concise, data_concise = await search_service.search(params, business_id=1)
    
    assert "John Doe (123)" in result_concise
    assert "Main St" not in result_concise
    assert "VIP" not in result_concise

@pytest.mark.asyncio
async def test_search_truncation(search_service):
    # Setup 15 results
    results = [Customer(name=f"C{i}") for i in range(15)]
    search_service.customer_repo.search.return_value = results
    
    params = SearchTool(query="all", entity_type="customer")
    result, data = await search_service.search(params, business_id=1)
    
    # Check that we only see 10 items formatted + truncation message
    # We can count newlines or check for specific names.
    # C0 to C9 should be present. C10 to C14 absent.
    assert "Customer: C0" in result
    assert "Customer: C9" in result
    assert "Customer: C10" not in result
    
    assert "...and 5 more results" in result
