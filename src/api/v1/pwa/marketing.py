import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models import User, Campaign
from src.api.dependencies.clerk_auth import get_current_user
from src.services.campaign_service import CampaignService
from src.services.search_service import SearchService
from src.services.geocoding import GeocodingService
from src.services.postmark_service import PostmarkService
from src.schemas.pwa import CampaignSchema, CampaignCreate

router = APIRouter()

def get_campaign_service(session: AsyncSession = Depends(get_db)):
    search_service = SearchService(session, GeocodingService())
    return CampaignService(session, search_service, PostmarkService())

@router.get("/", response_model=List[CampaignSchema])
async def list_campaigns(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Campaign).where(Campaign.business_id == current_user.business_id).order_by(Campaign.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()

@router.post("/preview")
async def preview_audience(
    query: str = "all",
    channel: str = "whatsapp",
    service: CampaignService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    # Mocking a temporary campaign ID or just using search service directly
    from src.uimodels import SearchTool
    search_params = SearchTool(
        query=query if query != "all" else "",
        entity_type="customer",
        detailed=False,
        query_type="all",
        min_date=None,
        max_date=None,
        status=None,
        radius=None,
        center_lat=None,
        center_lon=None,
        center_address=None,
        pipeline_stage=None
    )
    results = await service.search_service._search_customers(
        search_params, 
        current_user.business_id, 
        None, 
        None
    )

    valid_results = []
    for customer in results:
        if channel == "email" and not customer.email:
            continue
        if channel in ["whatsapp", "sms"] and not customer.phone:
            continue
        valid_results.append(customer)

    return {
        "count": len(valid_results),
        "samples": [c.name for c in valid_results[:3]]
    }

@router.post("/", response_model=CampaignSchema)
async def create_campaign(
    campaign_data: CampaignCreate,
    service: CampaignService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    try:
        # Create campaign
        campaign = await service.create_campaign(
            business_id=current_user.business_id,
            name=campaign_data.name,
            channel=campaign_data.channel,
            body=campaign_data.body,
            subject=campaign_data.subject,
            recipient_query=campaign_data.recipient_query
        )
        # Prepare audience
        await service.prepare_audience(campaign.id)
        return campaign
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{campaign_id}", response_model=CampaignSchema)
async def get_campaign(
    campaign_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    campaign = await session.get(Campaign, campaign_id)
    if not campaign or campaign.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign

@router.post("/{campaign_id}/execute")
async def execute_campaign(
    campaign_id: int,
    service: CampaignService = Depends(get_campaign_service),
    current_user: User = Depends(get_current_user)
):
    campaign = await service.session.get(Campaign, campaign_id)
    if not campaign or campaign.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Run execution in background
    asyncio.create_task(service.execute_campaign(campaign_id))
    return {"status": "started", "campaign_id": campaign_id}
