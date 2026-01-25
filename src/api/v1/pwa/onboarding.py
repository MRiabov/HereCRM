from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from src.database import get_db
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, UserRole, Business, ConversationStatus
from src.services.invitation import InvitationService
from src.repositories import UserRepository, BusinessRepository, ConversationStateRepository

router = APIRouter()

class OnboardingChoice(BaseModel):
    choice: str  # "create" or "join"
    invite_code: Optional[str] = None

@router.post("/choice")
async def process_onboarding_choice(
    payload: OnboardingChoice,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle the user's choice to either keep their auto-created business 
    or join an existing one via invite code.
    """
    user_repo = UserRepository(db)
    biz_repo = BusinessRepository(db)
    state_repo = ConversationStateRepository(db)
    invitation_service = InvitationService(db)

    if payload.choice == "create":
        # They already have a business (created in sync_clerk_user)
        # We just need to ensure their state is IDLE
        state = await state_repo.get_or_create(current_user.id)
        state.state = ConversationStatus.IDLE
        await db.commit()
        return {"status": "success", "message": "Business setup confirmed"}

    elif payload.choice == "join":
        if not payload.invite_code:
            raise HTTPException(status_code=400, detail="Invite code required to join a business")
        
        # Use phone or email as identifier
        identifier = current_user.phone_number or current_user.email or str(current_user.id)
        
        success, message, updated_user = await invitation_service.process_join(identifier, code=payload.invite_code)
        
        if success:
            # If they joined another business, they might have an orphan business created during signup.
            # For now we'll just leave it or we could delete if it has no data.
            
            state = await state_repo.get_or_create(current_user.id)
            state.state = ConversationStatus.IDLE
            await db.commit()
            return {"status": "success", "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)

    else:
        raise HTTPException(status_code=400, detail="Invalid choice. Must be 'create' or 'join'.")
