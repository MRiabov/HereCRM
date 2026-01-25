import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from src.database import get_db
from src.models import User, UserRole, ConversationStatus
from src.services.invitation import InvitationService
from src.repositories import BusinessRepository, ConversationStateRepository
from src.api.dependencies.clerk_auth import get_current_user, verify_token

logger = logging.getLogger(__name__)

router = APIRouter()

class OnboardingChoice(BaseModel):
    choice: str  # "create" or "join"
    invite_code: Optional[str] = None
    business_name: Optional[str] = None

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
    biz_repo = BusinessRepository(db)
    state_repo = ConversationStateRepository(db)
    invitation_service = InvitationService(db)

    if payload.choice == "create":
        # They already have a business (created in sync_clerk_user/JIT)
        # We rename it if requested and ensure they are OWNER
        if payload.business_name:
            business = await biz_repo.get_by_id_global(current_user.business_id)
            if business:
                business.name = payload.business_name
        
        current_user.role = UserRole.OWNER
        
        # Ensure their state is IDLE
        state = await state_repo.get_or_create(current_user.id)
        state.state = ConversationStatus.IDLE
        
        await db.commit()
        
        if not current_user.clerk_id:
            logger.error(f"User {current_user.id} has no clerk_id during onboarding")
            return {"status": "success", "message": "Business setup confirmed (local)"}

        # Update Clerk Metadata so PWA can redirect
        try:
            await verify_token.clerk_client.users.update_metadata_async(
                user_id=current_user.clerk_id,
                public_metadata={
                    "business_id": current_user.business_id,
                    "role": "OWNER"
                }
            )
        except Exception as e:
            # We don't want to fail the whole request if Clerk sync fails, 
            # but we should log it.
            print(f"Error updating Clerk metadata: {e}")

        return {"status": "success", "message": "Business setup confirmed"}

    elif payload.choice == "join":
        if not payload.invite_code:
            raise HTTPException(status_code=400, detail="Invite code required to join a business")
        
        # Use phone or email as identifier
        identifier = current_user.phone_number or current_user.email or str(current_user.id)
        
        success, message, updated_user = await invitation_service.process_join(identifier, code=payload.invite_code)
        
        if success:
            state = await state_repo.get_or_create(current_user.id)
            state.state = ConversationStatus.IDLE
            
            # Link the Clerk ID to the user if not already done (it should be)
            if updated_user and not updated_user.clerk_id:
                updated_user.clerk_id = current_user.clerk_id
            
            await db.commit()

            if not current_user.clerk_id:
                logger.error(f"User {current_user.id} has no clerk_id during join")
                return {"status": "success", "message": message}

            # Update Clerk Metadata
            try:
                # updated_user is guaranteed to be set if success is True
                biz_id = updated_user.business_id if updated_user else current_user.business_id
                role_val = updated_user.role.value if updated_user else UserRole.EMPLOYEE.value

                await verify_token.clerk_client.users.update_metadata_async(
                    user_id=current_user.clerk_id,
                    public_metadata={
                        "business_id": biz_id,
                        "role": role_val
                    }
                )
            except Exception as e:
                print(f"Error updating Clerk metadata: {e}")

            return {"status": "success", "message": message}
        else:
            raise HTTPException(status_code=400, detail=message)

    else:
        raise HTTPException(status_code=400, detail="Invalid choice. Must be 'create' or 'join'.")
