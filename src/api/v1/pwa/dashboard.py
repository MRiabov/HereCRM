from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timezone

from src.database import get_db
from src.api.dependencies.clerk_auth import verify_token
from src.models import (
    Customer,
    PipelineStage,
    Payment,
    PaymentStatus,
    Invoice,
    Job,
    User,
)

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    user: User = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    business_id = user.business_id
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Monthly Revenue
    # Sum of payments completed this month for this business
    revenue_stmt = (
        select(func.sum(Payment.amount))
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .join(Job, Invoice.job_id == Job.id)
        .where(
            and_(
                Job.business_id == business_id,
                Payment.status == PaymentStatus.COMPLETED,
                Payment.payment_date >= start_of_month,
            )
        )
    )
    revenue_result = await db.execute(revenue_stmt)
    revenue_monthly = revenue_result.scalar() or 0.0

    # 2. Pipeline Breakdown
    # Count customers in each stage for this business
    pipeline_stmt = (
        select(Customer.pipeline_stage, func.count(Customer.id))
        .where(Customer.business_id == business_id)
        .group_by(Customer.pipeline_stage)
    )
    pipeline_result = await db.execute(pipeline_stmt)
    pipeline_breakdown = {stage.name: count for stage, count in pipeline_result.all()}

    # Ensure all stages are present with 0 if not found (optional, but good for UI)
    for stage in PipelineStage:
        if stage.name not in pipeline_breakdown:
            pipeline_breakdown[stage.name] = 0

    # 3. Active Leads Count
    # Define "Active" as: NEW_LEAD, NOT_CONTACTED, CONTACTED, QUOTED
    # Exclude: LOST, NOT_INTERESTED, CONVERTED_ONCE, CONVERTED_RECURRENT
    active_stages = [
        PipelineStage.NEW_LEAD,
        PipelineStage.NOT_CONTACTED,
        PipelineStage.CONTACTED,
        PipelineStage.QUOTED,
    ]
    # We can calculate this from the breakdown
    active_leads_count = sum(pipeline_breakdown.get(stage.name, 0) for stage in active_stages)

    return {
        "revenue_monthly": revenue_monthly,
        "active_leads_count": active_leads_count,
        "pipeline_breakdown": pipeline_breakdown,
    }
