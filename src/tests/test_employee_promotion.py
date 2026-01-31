import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from src.main import app
from src.api.dependencies.clerk_auth import verify_token, get_current_user
from src.models import User, UserRole, Business


@pytest.fixture
def owner_user():
    return User(
        id=1,
        name="Owner",
        role=UserRole.OWNER,
        business_id=1,
        clerk_id="owner_clerk",
    )


@pytest.fixture
def manager_user():
    return User(
        id=2,
        name="Manager",
        role=UserRole.MANAGER,
        business_id=1,
        clerk_id="manager_clerk",
    )


@pytest.fixture
def employee_user():
    return User(
        id=3,
        name="Employee",
        role=UserRole.EMPLOYEE,
        business_id=1,
        clerk_id="employee_clerk",
    )


@pytest.fixture
async def setup_data(session: AsyncSession, owner_user, manager_user, employee_user):
    biz = Business(id=1, name="Test Biz")
    session.add(biz)
    session.add_all([owner_user, manager_user, employee_user])
    await session.commit()


@pytest.mark.asyncio
async def test_owner_can_promote_employee(
    session: AsyncSession, setup_data, owner_user, employee_user
):
    app.dependency_overrides[verify_token] = lambda: owner_user
    app.dependency_overrides[get_current_user] = lambda: owner_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/pwa/business/employees/{employee_user.id}/role",
            json={"role": "MANAGER"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["new_role"] == "MANAGER"


@pytest.mark.asyncio
async def test_manager_can_promote_employee(
    session: AsyncSession, setup_data, manager_user, employee_user
):
    app.dependency_overrides[verify_token] = lambda: manager_user
    app.dependency_overrides[get_current_user] = lambda: manager_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/pwa/business/employees/{employee_user.id}/role",
            json={"role": "MANAGER"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["new_role"] == "MANAGER"


@pytest.mark.asyncio
async def test_employee_cannot_promote_anyone(
    session: AsyncSession, setup_data, employee_user, manager_user
):
    app.dependency_overrides[verify_token] = lambda: employee_user
    app.dependency_overrides[get_current_user] = lambda: employee_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/pwa/business/employees/{manager_user.id}/role",
            json={"role": "MANAGER"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_change_owner_role(session: AsyncSession, setup_data, owner_user):
    app.dependency_overrides[verify_token] = lambda: owner_user
    app.dependency_overrides[get_current_user] = lambda: owner_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            f"/api/v1/pwa/business/employees/{owner_user.id}/role",
            json={"role": "EMPLOYEE"},
        )

    app.dependency_overrides.clear()
    assert response.status_code == 403
    assert "Cannot change role of an owner" in response.json()["detail"]
