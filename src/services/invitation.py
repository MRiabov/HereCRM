import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Invitation, InvitationStatus, User, UserRole, MessageTriggerSource, MessageType
from src.repositories import InvitationRepository, UserRepository, BusinessRepository
from src.services.messaging_service import messaging_service

logger = logging.getLogger(__name__)

class InvitationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.invitation_repo = InvitationRepository(session)
        self.user_repo = UserRepository(session)
        self.business_repo = BusinessRepository(session)

    async def create_invitation(self, business_id: int, inviter_id: int, identifier: str) -> Invitation:
        """
        Create a new invitation and send a notification to the invitee.
        If an active invitation already exists for this business, it refreshes it.
        """
        # Check for existing pending invitation
        existing_invites = await self.invitation_repo.get_pending_by_identifier(identifier)
        invitation = None
        
        for invite in existing_invites:
            if invite.business_id == business_id:
                invitation = invite
                break
        
        if invitation:
            # Refresh existing invitation
            invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        else:
            # Create new invitation
            token = secrets.token_urlsafe(16)
            invitation = Invitation(
                business_id=business_id,
                inviter_id=inviter_id,
                invitee_identifier=identifier,
                token=token,
                status=InvitationStatus.PENDING,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )
            self.invitation_repo.add(invitation)
        
        await self.session.commit()
        await self.session.refresh(invitation)

        # Send message via MessagingService
        business = await self.business_repo.get_by_id_global(business_id)
        business_name = business.name if business else "a business"
        
        message = (
            f"You have been invited to join {business_name} on HereCRM. "
            f"Type 'Join' to accept and start your onboarding."
        )
        
        try:
            await messaging_service.send_message(
                recipient_phone=identifier,
                content=message,
                channel=MessageType.WHATSAPP,  # Default to WhatsApp
                trigger_source=MessageTriggerSource.INVITATION_FLOW,
                business_id=business_id
            )
        except Exception as e:
            logger.error(f"Failed to send invitation message to {identifier}: {e}")

        return invitation

    async def process_join(self, identifier: str, code: Optional[str] = None) -> tuple[bool, str, Optional[User]]:
        """
        Process a 'Join' command from a user (potential employee).
        Finds pending invitations and adds the user to the business.
        """
        invite = None
        if code:
            # First check if it's a persistent business invite code
            business = await self.business_repo.get_by_invite_code(code)
            if business:
                # Create a shim 'invite' object or handle logic directly
                # For consistency with existing logic, let's just use business_id from it
                business_id = business.id
            else:
                # Fall back to checking Invitation token
                invite = await self.invitation_repo.get_by_token(code)
                if not invite or invite.status != InvitationStatus.PENDING:
                    return False, "Invalid or expired invitation code.", None
                business_id = invite.business_id
                # Mark as accepted
                invite.status = InvitationStatus.ACCEPTED
        else:
            pending = await self.invitation_repo.get_pending_by_identifier(identifier)
            if not pending:
                return False, "No pending invitations found for your number.", None
            # Logic for multiple pending invites:
            # For this MVP we'll take the most recent one.
            invite = pending[0]
            business_id = invite.business_id
            # Mark as accepted
            invite.status = InvitationStatus.ACCEPTED
        
        # Create or Update User
        existing_user = await self.user_repo.get_by_phone(identifier)
        if not existing_user and "@" in identifier:
            existing_user = await self.user_repo.get_by_email(identifier)
        user = existing_user
        
        if existing_user:
            # If user exists, we transfer them to the new business
            # This implicitly removes them from the old business
            existing_user.business_id = business_id
            existing_user.role = UserRole.EMPLOYEE
            existing_user.preferences = {"confirm_by_default": False} # Reset or keep? Let's keep existing props but ensuring basics
        else:
            # Create new user
            user = User(
                phone_number=identifier,
                business_id=business_id,
                role=UserRole.EMPLOYEE,
                timezone="UTC"
            )
            self.user_repo.add(user)
        
        await self.session.commit()
        await self.session.refresh(user)
        
        # Fetch business name for welcome message
        business = await self.business_repo.get_by_id_global(business_id)
        business_name = business.name if business else "the business"
        
        return True, f"Welcome to {business_name}! You are now added to the team.", user
