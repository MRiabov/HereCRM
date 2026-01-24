from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.crm_service import CRMService
from src.schemas.pwa import CustomerSchema, CustomerCreate
from src.models import Customer, PipelineStage

router = APIRouter()

async def get_crm_service(session: AsyncSession = Depends(get_db)) -> CRMService:
    # HARDCODED BUSINESS ID = 1
    return CRMService(session, business_id=1)

@router.get("/", response_model=List[CustomerSchema])
async def list_customers(
    search: Optional[str] = None,
    service: CRMService = Depends(get_crm_service)
):
    if search:
        customers = await service.customer_repo.search(search, service.business_id)
    else:
        # TODO: Implement pagination in repo
        customers = await service.customer_repo.get_all(service.business_id)
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
    # Check if exists? (Optional validation)
    
    new_customer = Customer(
        business_id=service.business_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        street=data.street,
        city=data.city,
        pipeline_stage=PipelineStage.NOT_CONTACTED
    )
    service.customer_repo.add(new_customer)
    await service.session.commit()
    await service.session.refresh(new_customer)
    return new_customer
