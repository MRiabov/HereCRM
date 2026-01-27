import pytest
from datetime import datetime, timezone
from src.models import Business, Customer, Request
from src.services.crm_service import CRMService

@pytest.mark.asyncio
async def test_request_api_crud(async_session):
    # 1. Setup Data
    business = Business(name="API Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(name="John Doe", business_id=business.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    crm_service = CRMService(async_session, business.id)

    # 2. Create Request
    request_data = {
        "description": "I need a leaking faucet fixed",
        "urgency": "High",
        "expected_value": 150.0,
        "follow_up_date": datetime.now(timezone.utc),
        "customer_id": customer.id
    }
    
    request = await crm_service.create_request(**request_data)
    assert request.id is not None
    assert request.description == "I need a leaking faucet fixed"
    assert request.urgency == "High"
    assert request.customer_id == customer.id

    # 3. List Requests
    requests = await crm_service.request_repo.search(query="faucet", business_id=business.id)
    assert len(requests) == 1
    assert requests[0].id == request.id

    # 4. Update Request
    request.urgency = "Medium"
    await async_session.commit()
    await async_session.refresh(request)
    assert request.urgency == "Medium"

    # 5. Get Request by ID
    fetched_request = await async_session.get(Request, request.id)
    assert fetched_request.id == request.id
    assert fetched_request.urgency == "Medium"

    # 6. Delete Request
    await async_session.delete(request)
    await async_session.commit()
    
    deleted_request = await async_session.get(Request, request.id)
    assert deleted_request is None

@pytest.mark.asyncio
async def test_request_search(async_session):
    business = Business(name="Search Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    crm_service = CRMService(async_session, business.id)

    # Create multiple requests
    await crm_service.create_request(description="Garden work", urgency="Low")
    await crm_service.create_request(description="Roof repair", urgency="High")
    await crm_service.create_request(description="Indoor painting", urgency="Medium")

    # Search for "roof"
    results = await crm_service.request_repo.search(query="roof", business_id=business.id)
    assert len(results) == 1
    assert "Roof" in results[0].description

    # Search for All
    results = await crm_service.request_repo.search(query="all", business_id=business.id)
    assert len(results) == 3

    # Filter by Urgency
    results = await crm_service.request_repo.search(query="all", business_id=business.id, urgency="High")
    assert len(results) == 1
    assert results[0].urgency == "High"
