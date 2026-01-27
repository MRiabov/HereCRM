from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.services.crm_service import CRMService
from src.services.dashboard_service import DashboardService
from src.schemas.pwa import JobListResponse, JobSchema, JobCreate, JobUpdate
from src.models import Job, User
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

async def get_services(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return CRMService(session, business_id=current_user.business_id, user_id=current_user.id), DashboardService(session)

@router.get("/", response_model=List[JobListResponse])
async def list_jobs(
    date_from: Optional[date] = None,
    customer_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    search: Optional[str] = None,
    unscheduled: bool = False,
    page: int = 1,
    limit: int = 50,
    services: tuple[CRMService, DashboardService] = Depends(get_services),
    current_user: User = Depends(get_current_user)
):
    """
    List jobs.
    If search is provided, returns jobs matching the query.
    If customer_id is provided, returns job history for that customer grouped by date.
    If unscheduled is true, returns jobs without schedule or assignment.
    Otherwise, returns daily schedule for employees (defaults to today).
    """
    crm_service, dashboard_service = services
    skip = (page - 1) * limit

    if unscheduled:
        jobs = await dashboard_service.get_unscheduled_jobs(crm_service.business_id)
        # Apply manual pagination for unscheduled as it's a specialized query
        return [
            JobListResponse(
                date="Unscheduled",
                jobs=[JobSchema.model_validate(j) for j in jobs[skip : skip + limit]]
            )
        ]

    if search is not None:
        jobs = await crm_service.job_repo.search(
            query=search, 
            business_id=crm_service.business_id,
            skip=skip,
            limit=limit
        )
        # Group search results by date
        from itertools import groupby
        jobs.sort(key=lambda x: x.scheduled_at.date() if x.scheduled_at else date.min, reverse=True)
        
        response = []
        for date_key, group in groupby(jobs, key=lambda x: x.scheduled_at.date() if x.scheduled_at else None):
             d_str = date_key.isoformat() if date_key else "Unscheduled"
             response.append(JobListResponse(
                 date=d_str,
                 jobs=[JobSchema.model_validate(j) for j in group]
             ))
        return response

    if customer_id:
        jobs = await crm_service.get_jobs_for_customer(customer_id, skip=skip, limit=limit)
        
        # Group by date
        from itertools import groupby
        
        # Ensure we sort by date for groupby
        jobs.sort(key=lambda x: x.scheduled_at.date() if x.scheduled_at else date.min, reverse=True)
        
        response = []
        for date_key, group in groupby(jobs, key=lambda x: x.scheduled_at.date() if x.scheduled_at else None):
             if date_key is None:
                 # Skip unscheduled for now or handle as specific group? 
                 # Let's put them in a catch-all group if vital, but usually history implies scheduled/done.
                 # If we want to show them, we can use a placeholder date string or current date?
                 # Schema expects date string.
                 d_str = "Unscheduled"
             else:
                 d_str = date_key.isoformat()
             
             response.append(JobListResponse(
                 date=d_str,
                 jobs=[JobSchema.model_validate(j) for j in group]
             ))
        return response

    target_date = date_from or datetime.now(timezone.utc).date()
    
    # Get schedules for all employees
    # DashboardService returns {User: [Job]}
    schedules = await dashboard_service.get_employee_schedules(
        crm_service.business_id, 
        target_date,
        timezone_str=current_user.timezone
    )
    
    daily_jobs = []
    seen_job_ids = set()
    
    for user, jobs in schedules.items():
        if employee_id and user and user.id != employee_id:
            continue
            
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
            scheduled_at=job_data.scheduled_at,
            estimated_duration=job_data.estimated_duration,
            employee_id=job_data.employee_id,
            postal_code=job_data.postal_code,
            items=[item.model_dump() for item in job_data.items] if job_data.items else None
        )
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
            scheduled_at=job_update.scheduled_at,
            estimated_duration=job_update.estimated_duration,
            employee_id=job_update.employee_id,
            location=job_update.location,
            postal_code=job_update.postal_code,
            items=[item.model_dump() for item in job_update.items] if job_update.items else None
        )
        return job
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
