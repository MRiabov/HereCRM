from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models import User, WhatsAppTemplate, WhatsAppTemplateCategory
from src.schemas.pwa import WhatsAppTemplateSchema, WhatsAppTemplateCreate
from src.api.dependencies.clerk_auth import get_current_user
from src.services.whatsapp_template_service import WhatsAppTemplateService

router = APIRouter()

def get_service(session: AsyncSession = Depends(get_db)):
    return WhatsAppTemplateService(session)

@router.get("/", response_model=List[WhatsAppTemplateSchema])
async def list_templates(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(WhatsAppTemplate).where(WhatsAppTemplate.business_id == current_user.business_id)
    result = await session.execute(stmt)
    return result.scalars().all()

@router.post("/", response_model=WhatsAppTemplateSchema)
async def create_template(
    data: WhatsAppTemplateCreate,
    service: WhatsAppTemplateService = Depends(get_service),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check if category is valid string and convert to Enum
        # If it's already a valid string for the enum, just pass it or cast it
        # The Enum is str, enum.Enum
        category_enum = WhatsAppTemplateCategory(data.category)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid category. Must be one of {[e.value for e in WhatsAppTemplateCategory]}"
        )

    return await service.create_template(
        business_id=current_user.business_id,
        name=data.name,
        category=category_enum,
        components=data.components,
        language=data.language
    )

@router.post("/sync")
async def sync_templates(
    service: WhatsAppTemplateService = Depends(get_service),
    current_user: User = Depends(get_current_user)
):
    await service.sync_templates(current_user.business_id)
    return {"status": "synced"}
