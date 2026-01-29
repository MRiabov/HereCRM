from datetime import date as date_cls
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models import User
from src.api.dependencies.clerk_auth import get_current_user
from src.tools.routing_tools import AutorouteToolExecutor
from src.services.template_service import TemplateService
from src.services.geocoding import GeocodingService
from src.schemas.pwa import (
    RoutingResponse,
    RouteSchema,
    RoutingStep as PWARoutingStep,
    RoutingMetrics as PWARoutingMetrics,
    JobSchema,
    GeocodeResponse,
)

router = APIRouter()


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_address(
    address: str,
    city: Optional[str] = None,
    country: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    geocoder = GeocodingService()
    (
        lat,
        lon,
        street,
        city_res,
        country_res,
        postal_code,
        full_address,
    ) = await geocoder.geocode(
        address,
        default_city=city
        or (
            current_user.preferences.get("default_city")
            if current_user.preferences
            else None
        ),
        default_country=country
        or (
            current_user.preferences.get("default_country")
            if current_user.preferences
            else None
        ),
        session=db,
        user_id=current_user.id,
    )

    await db.commit()  # Important to commit the geocoding count increment

    return GeocodeResponse(
        latitude=lat,
        longitude=lon,
        street=street,
        city=city_res,
        country=country_res,
        postal_code=postal_code,
        full_address=full_address,
    )


@router.get("/", response_model=RoutingResponse)
async def get_routing_preview(
    date: Optional[date_cls] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
            pwa_steps.append(
                PWARoutingStep(
                    job_id=step.job.id,
                    arrival_time=step.arrival_time,
                    departure_time=step.departure_time,
                    distance_to_next=None,  # ORS might provide this in future
                    duration_to_next=None,
                    job=JobSchema.model_validate(step.job),
                )
            )

        pwa_routes.append(
            RouteSchema(
                employee_id=emp_id, employee_name=emp_map.get(emp_id), steps=pwa_steps
            )
        )

    metrics = PWARoutingMetrics(
        total_distance=solution.metrics.get("distance", 0),
        total_duration=solution.metrics.get("duration", 0),
        jobs_assigned=sum(len(s) for s in solution.routes.values()),
        unassigned_count=len(solution.unassigned_jobs),
    )

    return RoutingResponse(
        date=target_date.isoformat(),
        metrics=metrics,
        routes=pwa_routes,
        unassigned_jobs=[JobSchema.model_validate(j) for j in solution.unassigned_jobs],
    )


@router.post("/apply")
async def apply_routing(
    date: Optional[date_cls] = None,
    notify: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    target_date = date or date_cls.today()
    template_service = TemplateService()
    executor = AutorouteToolExecutor(db, current_user.business_id, template_service)

    solution, result = await executor._calculate(target_date)

    if isinstance(result, str):
        raise HTTPException(status_code=400, detail=result)

    result_msg = await executor.apply_schedule(solution, notify)
    return {"message": result_msg}
