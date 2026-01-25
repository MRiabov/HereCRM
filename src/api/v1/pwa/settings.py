from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from src.database import get_db
from src.services.workflow import WorkflowSettingsService
from src.schemas.pwa import BusinessSettingsSchema, BusinessSettingsUpdate
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, UserRole

router = APIRouter()

async def get_settings_service(
    session: AsyncSession = Depends(get_db)
) -> WorkflowSettingsService:
    return WorkflowSettingsService(session)

@router.get("/workflow", response_model=BusinessSettingsSchema)
async def get_workflow_settings(
    current_user: User = Depends(get_current_user),
    service: WorkflowSettingsService = Depends(get_settings_service)
):
    business = await service.business_repo.get_by_id_global(current_user.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    settings = await service.get_settings(current_user.business_id)
    
    return BusinessSettingsSchema(
        **settings,
        stripe_connected=business.quickbooks_connected
    )

@router.patch("/workflow", response_model=BusinessSettingsSchema)
async def update_workflow_settings(
    update_data: BusinessSettingsUpdate,
    current_user: User = Depends(get_current_user),
    service: WorkflowSettingsService = Depends(get_settings_service)
):
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can modify settings")
        
    business = await service.business_repo.get_by_id_global(current_user.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    # Filter out None values to avoid overwriting with None if not provided in PATCH
    updates = update_data.model_dump(exclude_unset=True)
    
    settings = await service.update_settings(current_user.business_id, **updates)
    await service.session.commit()
    
    return BusinessSettingsSchema(
        **settings,
        stripe_connected=business.quickbooks_connected
    )
