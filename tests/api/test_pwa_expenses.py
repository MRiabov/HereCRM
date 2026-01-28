import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from datetime import datetime, timezone
from src.database import get_db
from src.models import User, Business, UserRole, Expense, ExpenseCategory
from src.api.dependencies.clerk_auth import get_current_user, verify_token

@pytest.fixture
async def client(async_session):
    # Setup a test user and business
    biz = Business(name="Test Biz PWA Expenses")
    async_session.add(biz)
    await async_session.flush()
    
    user = User(
        clerk_id="pwa_expenses_test_user",
        name="PWA Developer",
        email="dev_expenses@example.com",
        business_id=biz.id,
        role=UserRole.OWNER
    )
    async_session.add(user)
    await async_session.flush()
    
    # Add some dummy expenses
    exp1 = Expense(
        business_id=biz.id,
        employee_id=user.id,
        amount=50.0,
        category=ExpenseCategory.FUEL,
        description="Gas for track",
        created_at=datetime.now(timezone.utc)
    )
    exp2 = Expense(
        business_id=biz.id,
        employee_id=user.id,
        amount=120.0,
        category=ExpenseCategory.TOOLS,
        description="New drill",
        created_at=datetime.now(timezone.utc)
    )
    async_session.add(exp1)
    async_session.add(exp2)
    
    await async_session.commit()
    await async_session.refresh(user)

    async def mock_auth():
        return user

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_auth
    app.dependency_overrides[verify_token] = mock_auth
    app.dependency_overrides[get_db] = lambda: async_session

    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test",
        headers={"Authorization": "Bearer dummy_pwa_token"}
    ) as c:
        yield c
    
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_list_expenses(client):
    response = await client.get("/api/v1/pwa/expenses/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["category"] in [ExpenseCategory.FUEL, ExpenseCategory.TOOLS]

@pytest.mark.asyncio
async def test_search_expenses(client):
    # Test search by category
    response = await client.get(f"/api/v1/pwa/expenses/?search={ExpenseCategory.FUEL.value}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == ExpenseCategory.FUEL
    
    # Test search by description
    response = await client.get("/api/v1/pwa/expenses/?search=drill")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == ExpenseCategory.TOOLS
    
    # Test no results
    response = await client.get("/api/v1/pwa/expenses/?search=Lunch")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
