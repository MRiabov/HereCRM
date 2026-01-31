import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import app
from src.api.dependencies.clerk_auth import verify_token, get_current_user
from src.models import User, UserRole, Business, Job, Customer, JobStatus
from datetime import datetime, timezone, date


@pytest.fixture
def manager_user():
    return User(
        id=1,
        name="Manager",
        role=UserRole.OWNER,
        business_id=1,
        timezone="UTC",
        clerk_id="manager_clerk",
    )


@pytest.fixture
def tech_user():
    return User(
        id=2,
        name="Tech",
        role=UserRole.EMPLOYEE,
        business_id=1,
        timezone="UTC",
        clerk_id="tech_clerk",
    )


@pytest.fixture
async def setup_data(session: AsyncSession, manager_user, tech_user):
    # Setup Business
    biz = Business(id=1, name="Test Biz")
    session.add(biz)

    # Add Users
    session.add(manager_user)
    session.add(tech_user)
    await session.flush()

    # Setup Customers
    c1 = Customer(id=1, name="Customer 1", business_id=1)
    session.add(c1)
    await session.flush()

    # Setup Jobs
    today = datetime.now(timezone.utc).replace(hour=10, minute=0)

    # Job for Manager
    j1 = Job(
        id=1,
        business_id=1,
        customer_id=1,
        employee_id=1,
        scheduled_at=today,
        description="Manager Job",
    )
    # Job for Tech
    j2 = Job(
        id=2,
        business_id=1,
        customer_id=1,
        employee_id=2,
        scheduled_at=today,
        description="Tech Job",
    )
    # Unscheduled Job
    j3 = Job(
        id=3,
        business_id=1,
        customer_id=1,
        employee_id=None,
        scheduled_at=None,
        description="Backlog Job",
        status=JobStatus.PENDING,
    )

    session.add_all([j1, j2, j3])
    await session.commit()


@pytest.mark.asyncio
async def test_manager_sees_all_jobs(session: AsyncSession, setup_data, manager_user):
    app.dependency_overrides[verify_token] = lambda: manager_user
    app.dependency_overrides[get_current_user] = lambda: manager_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/pwa/jobs/")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    # Manager should see both scheduled jobs
    jobs = [j["description"] for j in data[0]["jobs"]]
    assert "Manager Job" in jobs
    assert "Tech Job" in jobs


@pytest.mark.asyncio
async def test_tech_sees_only_own_jobs(session: AsyncSession, setup_data, tech_user):
    app.dependency_overrides[verify_token] = lambda: tech_user
    app.dependency_overrides[get_current_user] = lambda: tech_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/pwa/jobs/")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    # Tech should only see their own job
    jobs = [j["description"] for j in data[0]["jobs"]]
    assert "Tech Job" in jobs
    assert "Manager Job" not in jobs


@pytest.mark.asyncio
async def test_tech_cannot_see_backlog(session: AsyncSession, setup_data, tech_user):
    app.dependency_overrides[verify_token] = lambda: tech_user
    app.dependency_overrides[get_current_user] = lambda: tech_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/pwa/jobs/", params={"unscheduled": True})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    # Tech should get an empty list for unscheduled
    assert data[0]["jobs"] == []


@pytest.mark.asyncio
async def test_manager_sees_backlog(session: AsyncSession, setup_data, manager_user):
    app.dependency_overrides[verify_token] = lambda: manager_user
    app.dependency_overrides[get_current_user] = lambda: manager_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/pwa/jobs/", params={"unscheduled": True})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    # Manager should see the backlog job
    jobs = [j["description"] for j in data[0]["jobs"]]
    assert "Backlog Job" in jobs


@pytest.mark.asyncio
async def test_tech_search_restricted(session: AsyncSession, setup_data, tech_user):
    app.dependency_overrides[verify_token] = lambda: tech_user
    app.dependency_overrides[get_current_user] = lambda: tech_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/api/v1/pwa/jobs/", params={"search": "Job"})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()

    # Collect all jobs from all date groups in search result
    all_jobs = []
    for group in data:
        all_jobs.extend(group["jobs"])

    jobs = [j["description"] for j in all_jobs]
    assert "Tech Job" in jobs
    assert "Manager Job" not in jobs
