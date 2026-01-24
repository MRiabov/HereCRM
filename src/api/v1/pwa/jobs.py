from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.dashboard_service import DashboardService
from src.schemas.pwa import JobListResponse, JobSchema, JobCreate, JobUpdate
from src.models import Job

router = APIRouter()

async def get_services(session: AsyncSession = Depends(get_db)):
    # HARDCODED BUSINESS ID = 1 FOR PROTOTYPE
    return CRMService(session, business_id=1), DashboardService(session)

@router.get("/", response_model=List[JobListResponse])
async def list_jobs(
    date_from: Optional[date] = None,
    services: tuple[CRMService, DashboardService] = Depends(get_services)
):
    """
    List jobs grouped by date. 
    Currently simplifies to returning today's jobs for the business owner/employees.
    Reference matching: DashboardService.get_employee_schedules
    """
    crm_service, dashboard_service = services
    target_date = date_from or datetime.now(timezone.utc).date()
    
    # Get schedules for all employees
    # DashboardService returns {User: [Job]}
    schedules = await dashboard_service.get_employee_schedules(crm_service.business_id, target_date)
    
    # Flatten to list of jobs for the response, since frontend expects a flat list or grouped by date?
    # The PWA 'Schedule' screen expects jobs for a specific day.
    # The schema `JobListResponse` expects `date` and `jobs`.
    
    daily_jobs = []
    seen_job_ids = set()
    
    for user, jobs in schedules.items():
        for job in jobs:
            if job.id not in seen_job_ids:
                daily_jobs.append(job)
                seen_job_ids.add(job.id)
    
    # Sort by time
    daily_jobs.sort(key=lambda x: x.scheduled_at or datetime.min.replace(tzinfo=timezone.utc))

    return [
        JobListResponse(
            date=target_date.isoformat(),
            jobs=[JobSchema.model_validate(j) for j in daily_jobs]
        )
    ]

@router.get("/{job_id}", response_model=JobSchema)
async def get_job(
    job_id: int,
    services: tuple[CRMService, DashboardService] = Depends(get_services)
):
    crm_service, _ = services
    job = await crm_service.job_repo.get_with_line_items(job_id, crm_service.business_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/", response_model=JobSchema)
async def create_job(
    job_data: JobCreate,
    services: tuple[CRMService, DashboardService] = Depends(get_services)
):
    crm_service, _ = services
    try:
        job = await crm_service.create_job(
            customer_id=job_data.customer_id,
            description=job_data.description,
            value=job_data.value,
            location=job_data.location,
            status=job_data.status,
            scheduled_at=job_data.scheduled_at
        )
    
        # Reload with customer for schema validation
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload
        stmt = select(Job).options(joinedload(Job.customer)).where(Job.id == job.id)
        result = await crm_service.session.execute(stmt)
        job = result.scalar_one()
        
        return job
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/{job_id}", response_model=JobSchema)
async def update_job(
    job_id: int,
    job_update: JobUpdate,
    services: tuple[CRMService, DashboardService] = Depends(get_services)
):
    crm_service, _ = services
    try:
        job = await crm_service.update_job(
            job_id=job_id,
            description=job_update.description,
            status=job_update.status,
            scheduled_at=job_update.scheduled_at
        )
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
