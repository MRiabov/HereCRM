import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import select

from src.models import Business, User, UserRole, ConversationStatus, Invitation, InvitationStatus
from src.services.whatsapp_service import WhatsappService
from src.services.invitation import InvitationService
from src.tools.employee_management import InviteUserTool

@pytest.mark.asyncio
async def test_invitation_flow_end_to_end(async_session):
    # 1. Setup Data
    business = Business(name="Test Biz")
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    owner = User(
        phone_number="owner_123",
        business_id=business.id,
        role=UserRole.OWNER,
        timezone="UTC",
        preferences={},
    )
    async_session.add(owner)
    await async_session.commit()
    await async_session.refresh(owner)

    # 2. Setup Service with mocked components
    mock_parser = AsyncMock()
    mock_template = MagicMock()
    
    def mock_render(key, **kwargs):
        if key == "welcome_back": return "Welcome back"
        if key == "welcome_message": return "Welcome to HereCRM"
        return f"[{key}]"
    mock_template.render.side_effect = mock_render
    
    # We need a real InvitationService connected to DB
    invitation_service = InvitationService(async_session)
    
    # Mock BillingService to avoid dependency
    mock_billing = AsyncMock()
    
    service = WhatsappService(
        session=async_session,
        parser=mock_parser,
        template_service=mock_template,
        billing_service=mock_billing
    )
    # Inject real service to ensure it uses the test session
    service.invitation_service = invitation_service

    # 3. Test: Enter Employee Management
    # Logic is hardcoded in _handle_idle for now
    msg = await service.handle_message("Employee Management", user_phone="owner_123")
    assert "Employee Management mode" in msg
    
    # Verify state
    from src.repositories import ConversationStateRepository
    state_repo = ConversationStateRepository(async_session)
    state = await state_repo.get_by_user_id(owner.id)
    assert state.state == ConversationStatus.EMPLOYEE_MANAGEMENT

    # 4. Test: Send Invite
    # Mock parser to return InviteUserTool when called with parse_employee_management
    invite_tool = InviteUserTool(identifier="+999888777")
    mock_parser.parse_employee_management.return_value = invite_tool
    
    msg = await service.handle_message("Invite +999888777", user_phone="owner_123")
    assert "Invitation sent" in msg
    
    # Verify DB Invitation
    stmt = select(Invitation).where(Invitation.invitee_identifier == "+999888777")
    res = await async_session.execute(stmt)
    invitation = res.scalar_one_or_none()
    assert invitation is not None
    assert invitation.status == InvitationStatus.PENDING
    assert invitation.business_id == business.id
    assert invitation.inviter_id == owner.id

    # 5. Test: Join
    # New user message logic
    # We need to simulate a NEW message from a NEW number
    # handle_message(is_new_user=False) initially, but internally it checks DB.
    # Since +999888777 is not in DB, it goes to "not user" block.
    
    msg = await service.handle_message("Join", user_phone="+999888777")
    assert "Welcome" in msg
    
    # Verify User created
    stmt = select(User).where(User.phone_number == "+999888777")
    res = await async_session.execute(stmt)
    new_user = res.scalar_one_or_none()
    assert new_user is not None
    assert new_user.business_id == business.id
    assert new_user.role == UserRole.EMPLOYEE

    # Verify Invitation Updated
    await async_session.refresh(invitation)
    assert invitation.status == InvitationStatus.ACCEPTED
