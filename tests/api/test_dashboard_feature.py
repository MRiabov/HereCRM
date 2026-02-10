import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db
from src.models import User, Business, UserRole, Job, JobStatus, PipelineStage, Customer
from src.api.dependencies.clerk_auth import get_current_user, verify_token
from datetime import datetime, timezone
import pytest_asyncio
from sqlalchemy import select

@pytest.fixture
async def client(async_session):
    # Setup a test user and business
    biz = Business(name="Test Biz Dashboard")
    async_session.add(biz)
    await async_session.flush()

    user = User(
        clerk_id="dashboard_test_user",
        name="Dashboard User",
        email="dash@example.com",
        business_id=biz.id,
        role=UserRole.OWNER,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    async def mock_auth():
        return user

    # Override dependencies
    app.dependency_overrides[get_current_user] = mock_auth
    app.dependency_overrides[verify_token] = mock_auth

    async def get_db_override():
        yield async_session

    app.dependency_overrides[get_db] = get_db_override

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer dummy_token"},
    ) as c:
        yield c

    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_dashboard_stats(client, async_session):
    # Get user to know business_id
    result = await async_session.execute(select(User).where(User.email == "dash@example.com"))
    user = result.scalar_one()
    business_id = user.business_id

    # Create some data
    # 1. Completed Job in current month for Revenue
    now = datetime.now(timezone.utc)

    # Customer for job
    customer1 = Customer(
        business_id=business_id,
        name="Cust 1",
        pipeline_stage=PipelineStage.CONVERTED_ONCE
    )
    async_session.add(customer1)
    await async_session.flush()

    job = Job(
        business_id=business_id,
        customer_id=customer1.id,
        description="Revenue Job",
        status=JobStatus.COMPLETED,
        value=100.0,
        completed_at=now,
        scheduled_at=now
    )
    async_session.add(job)

    # 2. Active Lead
    customer2 = Customer(
        business_id=business_id,
        name="Lead 1",
        pipeline_stage=PipelineStage.NEW_LEAD
    )
    async_session.add(customer2)

    await async_session.commit()

    response = await client.get("/api/v1/pwa/dashboard/stats")
    assert response.status_code == 200
    data = response.json()

    # Debug print if fails
    print(data)

    assert data["revenue_monthly"] == 100.0
    assert data["active_leads_count"] == 1
    assert "pipeline_breakdown" in data
    # Check NEW_LEAD count
    assert data["pipeline_breakdown"]["NEW_LEAD"]["count"] == 1
