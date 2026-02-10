from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from datetime import datetime, timezone

from src.database import get_db
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, PipelineStage
from src.repositories import JobRepository, CustomerRepository
from src.schemas.pwa import DashboardStats, PipelineStageStats

router = APIRouter()

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    business_id = current_user.business_id
    job_repo = JobRepository(db)
    customer_repo = CustomerRepository(db)

    # 1. Monthly Revenue
    now = datetime.now(timezone.utc)
    monthly_revenue = await job_repo.get_monthly_revenue(business_id, now.year, now.month)

    # 2. Pipeline Breakdown
    pipeline_summary = await customer_repo.get_pipeline_summary(business_id)

    # Extract breakdown
    pipeline_breakdown = {}
    active_leads_count = 0

    for stage, data in pipeline_summary.items():
        # PipelineStageStats expects count and value.
        pipeline_breakdown[stage.value] = PipelineStageStats(
            count=data["count"],
            value=data["value"]
        )

        # Calculate active leads
        if stage in [PipelineStage.NEW_LEAD, PipelineStage.NOT_CONTACTED]:
            active_leads_count += data["count"]

    return DashboardStats(
        revenue_monthly=monthly_revenue,
        active_leads_count=active_leads_count,
        pipeline_breakdown=pipeline_breakdown
    )
