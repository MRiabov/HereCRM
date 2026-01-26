from datetime import date as date_cls
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import User, Job
from src.api.dependencies.clerk_auth import get_current_user
from src.tools.routing_tools import AutorouteToolExecutor
from src.services.template_service import TemplateService
from src.schemas.pwa import (
    RoutingResponse, 
    RouteSchema, 
    RoutingStep as PWARoutingStep, 
    RoutingMetrics as PWARoutingMetrics,
    JobSchema,
    CustomerSchema,
    UserSchema
)

router = APIRouter()

@router.get("/", response_model=RoutingResponse)
async def get_routing_preview(
    date: Optional[date_cls] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_date = date or date_cls.today()
    template_service = TemplateService()
    executor = AutorouteToolExecutor(db, current_user.business_id, template_service)
    
    solution, result = await executor._calculate(target_date)
    
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    
    employees = result
    emp_map = {e.id: e.name or e.email or f"Technician {e.id}" for e in employees}
    
    pwa_routes = []
    for emp_id, steps in solution.routes.items():
        pwa_steps = []
        for step in steps:
            pwa_steps.append(PWARoutingStep(
                job_id=step.job.id,
                arrival_time=step.arrival_time,
                departure_time=step.departure_time,
                distance_to_next=None, # ORS might provide this in future
                duration_to_next=None,
                job=JobSchema.model_validate(step.job)
            ))
        
        pwa_routes.append(RouteSchema(
            employee_id=emp_id,
            employee_name=emp_map.get(emp_id),
            steps=pwa_steps
        ))
    
    metrics = PWARoutingMetrics(
        total_distance=solution.metrics.get("distance", 0),
        total_duration=solution.metrics.get("duration", 0),
        jobs_assigned=sum(len(s) for s in solution.routes.values()),
        unassigned_count=len(solution.unassigned_jobs)
    )
    
    return RoutingResponse(
        date=target_date.isoformat(),
        metrics=metrics,
        routes=pwa_routes,
        unassigned_jobs=[JobSchema.model_validate(j) for j in solution.unassigned_jobs]
    )

@router.post("/apply")
async def apply_routing(
    date: Optional[date_cls] = None,
    notify: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_date = date or date_cls.today()
    template_service = TemplateService()
    executor = AutorouteToolExecutor(db, current_user.business_id, template_service)
    
    solution, result = await executor._calculate(target_date)
    
    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)
    
    result_msg = await executor.apply_schedule(solution, notify)
    return {"message": result_msg}
