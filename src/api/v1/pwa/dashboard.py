from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.dashboard_service import DashboardService
from src.schemas.pwa import DashboardStats, RecentActivity

router = APIRouter()

async def get_dashboard_services(session: AsyncSession = Depends(get_db)):
    # Assuming authenticated user context is handled via middleware or another dependency
    # For now, we instantiate services directly with session.
    # In a real scenario, we'd extract business_id from the authenticated user.
    # HARDCODED BUSINESS ID = 1 FOR PROTOTYPE
    return CRMService(session, business_id=1), DashboardService(session)

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    services: tuple[CRMService, DashboardService] = Depends(get_dashboard_services)
):
    crm_service, dashboard_service = services
    
    # Fetch Pipeline Summary
    pipeline_data = await crm_service.get_pipeline_summary()
    
    # Calculate totals
    # TODO: Implement real revenue calculation in CRMService or BillingService.
    # For now, mocking revenue to match UI or simple calculation if easy.
    revenue = 12450.00 # Placeholder from UI
    
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
    # TODO: Fetch real activity logs (MessageLog, Job updates, etc.)
    # For now returning empty list or mocks could be better
    from datetime import datetime, timezone, timedelta
    
    # Mock data to match UI feel for now
    return [
        RecentActivity(
            type="invoice",
            title="Invoice Sent",
            description="Invoice #1024 sent to Alice Smith for $120.00",
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=2)
        ),
        RecentActivity(
            type="lead",
            title="New Lead",
            description="Contact from John O'Connor regarding 'Leaky Faucet'",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3)
        )
    ]
