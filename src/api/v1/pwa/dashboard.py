from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.dashboard_service import DashboardService
from src.schemas.pwa import DashboardStats, RecentActivity
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User

router = APIRouter()

async def get_dashboard_services(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CRMService(session, business_id=current_user.business_id), DashboardService(session)

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    services: tuple[CRMService, DashboardService] = Depends(get_dashboard_services)
):
    crm_service, dashboard_service = services
    
    # Fetch Pipeline Summary
    pipeline_data = await crm_service.get_pipeline_summary()
    
    # Calculate totals
    revenue = await dashboard_service.get_monthly_revenue(crm_service.business_id)
    
    active_leads = 0
    needs_followup = 0
    
    # Sum up leads from pipeline data
    for stage, data in pipeline_data.items():
        if stage in ["contacted", "not_contacted"]:
            active_leads += data["count"]
            if stage == "contacted":
                needs_followup += data["count"] # Simplistic logic
                
    return DashboardStats(
        revenue_monthly=revenue,
        active_leads_count=active_leads,
        leads_need_followup=needs_followup,
        pipeline_breakdown=pipeline_data
    )

@router.get("/recent-activity", response_model=List[RecentActivity])
async def get_recent_activity(
    services: tuple[CRMService, DashboardService] = Depends(get_dashboard_services)
):
    crm_service, dashboard_service = services
    activities = await dashboard_service.get_recent_activity(crm_service.business_id)
    return [RecentActivity(**a) for a in activities]
