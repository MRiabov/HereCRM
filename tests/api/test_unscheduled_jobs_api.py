import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.api.dependencies.clerk_auth import get_current_user, verify_token
from src.database import get_db
from src.models import User, Business, UserRole, Customer, Job, JobStatus
from datetime import datetime, timezone
from sqlalchemy import select


@pytest.fixture
async def client(async_session):
    # Setup a test user and business
    biz = Business(name="Test Biz Unscheduled")
    async_session.add(biz)
    await async_session.flush()

    user = User(
        clerk_id="unscheduled_test_user",
        name="Manager User",
        email="manager@example.com",
        business_id=biz.id,
        role=UserRole.MANAGER,
    )
    async_session.add(user)
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
        headers={"Authorization": "Bearer dummy_token"},
    ) as c:
        yield c

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_list_unscheduled_jobs_api(client, async_session):
    # Get the business we created in fixture
    stmt = select(Business).where(Business.name == "Test Biz Unscheduled")
    result = await async_session.execute(stmt)
    biz = result.scalar_one()

    customer = Customer(name="Unscheduled Customer", business_id=biz.id)
    async_session.add(customer)
    await async_session.commit()
    await async_session.refresh(customer)

    # 1. Unscheduled job
    job1 = Job(
        business_id=biz.id,
        customer_id=customer.id,
        description="Backlog Job",
        status=JobStatus.PENDING,
        scheduled_at=None,
        employee_id=1,
    )

    # 2. Scheduled job
    job2 = Job(
        business_id=biz.id,
        customer_id=customer.id,
        description="Scheduled Job",
        status=JobStatus.PENDING,
        scheduled_at=datetime.now(timezone.utc),
        employee_id=1,
    )

    async_session.add_all([job1, job2])
    await async_session.commit()

    # Test unscheduled listing
    response = await client.get("/api/v1/pwa/jobs/?unscheduled=true")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["date"] == "Unscheduled"
    assert len(data[0]["jobs"]) == 1
    assert data[0]["jobs"][0]["description"] == "Backlog Job"
    # Verify related data is present (JobSchema uses CustomerSchema)
    assert data[0]["jobs"][0]["customer"]["name"] == "Unscheduled Customer"
