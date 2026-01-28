from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.database import get_db
from src.models import Service, User
from src.schemas.pwa import ServiceSchema, ServiceCreate
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ServiceSchema])
async def list_services(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List services for the current business.
    """
    stmt = select(Service).where(Service.business_id == current_user.business_id).order_by(Service.name.asc())
    result = await db.execute(stmt)
    services = result.scalars().all()
    return services

@router.post("/", response_model=ServiceSchema)
async def create_service(
    service_in: ServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new service in the catalog.
    """
    service = Service(
        business_id=current_user.business_id,
        name=service_in.name,
        description=service_in.description,
        default_price=service_in.default_price,
        estimated_duration=service_in.estimated_duration
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service

@router.get("/{service_id}", response_model=ServiceSchema)
async def get_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get service details by ID.
    """
    service = await db.get(Service, service_id)
    if not service or service.business_id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
