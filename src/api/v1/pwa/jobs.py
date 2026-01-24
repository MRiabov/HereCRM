from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.dashboard_service import DashboardService
from src.repositories import JobRepository
from src.schemas.pwa import JobSchema, JobCreate, JobUpdate, JobListResponse
from src.models import User

router = APIRouter()

async def get_services(session: AsyncSession = Depends(get_db)):
    # HARDCODED BUSINESS ID = 1 FOR PROTOTYPE
    return CRMService(session, business_id=1), DashboardService(session), JobRepository(session)

@router.get("/", response_model=List[JobSchema])
async def list_jobs(
    date_from: date = Query(..., description="Start date for filtering"),
    services: tuple = Depends(get_services)
):
    crm, dashboard, job_repo = services
    business_id = 1 # Hardcoded
    
    # Query Jobs directly with eager loading
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.models import Job
    
    # Simple query for the date
    # We want jobs where scheduled_at is on that date.
    start_of_day = datetime.combine(date_from, datetime.min.time())
    end_of_day = datetime.combine(date_from, datetime.max.time())
    
    query = (
        select(Job)
        .where(Job.scheduled_at >= start_of_day, Job.scheduled_at <= end_of_day)
        .options(selectinload(Job.customer), selectinload(Job.employee))
        .order_by(Job.scheduled_at.asc())
    )
    result = await job_repo.session.execute(query)
    all_jobs = result.scalars().all()
    
    return all_jobs

@router.get("/{job_id}", response_model=JobSchema)
async def get_job(
    job_id: int,
    services: tuple = Depends(get_services)
):
    crm, dashboard, job_repo = services
    business_id = 1
    
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.models import Job

    query = (
        select(Job)
        .where(Job.id == job_id, Job.business_id == business_id)
        .options(selectinload(Job.customer), selectinload(Job.employee))
    )
    result = await job_repo.session.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/", response_model=JobSchema)
async def create_job(
    payload: JobCreate,
    services: tuple = Depends(get_services)
):
    crm, dashboard, job_repo = services
    
    job = await crm.create_job(
        customer_id=payload.customer_id,
        description=payload.description,
        value=payload.value,
        location=payload.location,
        status=payload.status,
        scheduled_at=payload.scheduled_at
    )
    
    # Reload to get relationships
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from src.models import Job
    
    query = (
        select(Job)
        .where(Job.id == job.id)
        .options(selectinload(Job.customer), selectinload(Job.employee))
    )
    result = await job_repo.session.execute(query)
    job = result.scalar_one()
    
    return job

@router.patch("/{job_id}", response_model=JobSchema)
async def update_job(
    job_id: int,
    payload: JobUpdate,
    services: tuple = Depends(get_services)
):
    crm, dashboard, job_repo = services
    
    try:
        job = await crm.update_job(
            job_id=job_id,
            description=payload.description,
            status=payload.status,
            scheduled_at=payload.scheduled_at
        )
        # Update employee if provided (not supported by crm.update_job directly yet)
        if payload.employee_id:
             job.employee_id = payload.employee_id
             await crm.session.commit()

        # Reload
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from src.models import Job
        query = (
            select(Job)
            .where(Job.id == job.id)
            .options(selectinload(Job.customer), selectinload(Job.employee))
        )
        result = await job_repo.session.execute(query)
        job = result.scalar_one()

        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
