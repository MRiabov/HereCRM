from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.crm_service import CRMService
from src.schemas.pwa import CustomerSchema, CustomerCreate, CustomerUpdate
from src.models import Customer, PipelineStage, User
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

async def get_crm_service(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CRMService:
    return CRMService(session, business_id=current_user.business_id, user_id=current_user.id)

@router.get("/", response_model=List[CustomerSchema])
async def list_customers(
    search: Optional[str] = None,
    pipeline_stage: Optional[PipelineStage] = None,
    page: int = 1,
    limit: int = 50,
    service: CRMService = Depends(get_crm_service)
):
    skip = (page - 1) * limit
    if search or pipeline_stage:
        customers = await service.customer_repo.search(
            query=search or "", 
            business_id=service.business_id,
            pipeline_stage=pipeline_stage,
            skip=skip,
            limit=limit
        )
    else:
        customers = await service.customer_repo.get_all(service.business_id, skip=skip, limit=limit)
        
    # Enrich with job stats
    if customers:
        customer_ids = [c.id for c in customers]
        stats = await service.customer_repo.get_stats_for_customers(customer_ids)
        for c in customers:
            c_stats = stats.get(c.id, {"job_count": 0, "total_value": 0.0})
            c.job_count = c_stats["job_count"]
            c.total_value = c_stats["total_value"]
            
    return customers


@router.get("/{customer_id}", response_model=CustomerSchema)
async def get_customer(
    customer_id: int,
    service: CRMService = Depends(get_crm_service)
):
    customer = await service.customer_repo.get_by_id(customer_id, service.business_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/", response_model=CustomerSchema)
async def create_customer(
    data: CustomerCreate,
    service: CRMService = Depends(get_crm_service)
):
    full_name = data.name
    if not full_name and (data.first_name or data.last_name):
        full_name = f"{data.first_name or ''} {data.last_name or ''}".strip()

    new_customer = Customer(
        business_id=service.business_id,
        name=full_name,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        email=data.email,
        street=data.street,
        city=data.city,
        pipeline_stage=data.pipeline_stage or PipelineStage.NOT_CONTACTED
    )
    service.customer_repo.add(new_customer)
    await service.session.commit()
    # await service.session.refresh(new_customer) # Causing InvalidRequestError in E2E tests with :memory: DB
    return new_customer

@router.patch("/{customer_id}", response_model=CustomerSchema)
async def update_customer(
    customer_id: int,
    data: CustomerUpdate,
    service: CRMService = Depends(get_crm_service)
):
    try:
        updated_customer = await service.update_customer(
            customer_id=customer_id,
            name=data.name,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            email=data.email,
            street=data.street,
            city=data.city,
            pipeline_stage=data.pipeline_stage
        )
        await service.session.commit()
        await service.session.refresh(updated_customer)
        return updated_customer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
