import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import get_db
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, Business, Invitation, InvitationStatus, ConversationStatus

@pytest.fixture
async def client(async_session):
    # Setup a test user and business
    biz = Business(name="Initial Biz")
    async_session.add(biz)
    await async_session.flush()
    
    user = User(
        clerk_id="user_pwa_test",
        name="PWA User",
        email="pwa@example.com",
        business_id=biz.id,
        role="owner"
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)

    async def mock_auth():
        return user

    # Override get_current_user
    app.dependency_overrides[get_current_user] = mock_auth
    
    # Override the verify_token dependency which is applied at router level
    from src.api.dependencies.clerk_auth import verify_token
    app.dependency_overrides[verify_token] = mock_auth
    
    app.dependency_overrides[get_db] = lambda: async_session

    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test",
        headers={"Authorization": "Bearer dummy_token"}
    ) as c:
        c.test_user = user
        yield c
    
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_pwa_onboarding_choice_create(client, async_session):
    payload = {"choice": "create"}
    response = await client.post("/api/v1/pwa/onboarding/choice", json=payload)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Business setup confirmed"
    
    # Verify state is IDLE
    from src.repositories import ConversationStateRepository
    state_repo = ConversationStateRepository(async_session)
    state = await state_repo.get_by_user_id(client.test_user.id)
    assert state.state == ConversationStatus.IDLE

@pytest.mark.asyncio
async def test_pwa_onboarding_choice_join(client, async_session):
    # Create another business and an invitation
    other_biz = Business(name="Joinable Biz")
    async_session.add(other_biz)
    await async_session.flush()
    
    inviter = User(phone_number="999", business_id=other_biz.id, role="owner")
    async_session.add(inviter)
    await async_session.flush()
    
    invite = Invitation(
        business_id=other_biz.id,
        inviter_id=inviter.id,
        invitee_identifier="pwa@example.com",
        token="PWA_JOIN_CODE",
        status=InvitationStatus.PENDING
    )
    async_session.add(invite)
    await async_session.commit()

    payload = {"choice": "join", "invite_code": "PWA_JOIN_CODE"}
    response = await client.post("/api/v1/pwa/onboarding/choice", json=payload)
    
    assert response.status_code == 200
    assert "Welcome to Joinable Biz!" in response.json()["message"]
    
    # Verify user's business_id updated
    await async_session.refresh(client.test_user)
    assert client.test_user.business_id == other_biz.id