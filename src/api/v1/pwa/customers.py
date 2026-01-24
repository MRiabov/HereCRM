from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.repositories import CustomerRepository
from src.schemas.pwa import CustomerSchema, CustomerCreate
from src.models import Customer, PipelineStage

router = APIRouter()

async def get_repo(session: AsyncSession = Depends(get_db)):
    return CustomerRepository(session)

@router.get("/", response_model=List[CustomerSchema])
async def list_customers(
    search: Optional[str] = None,
    # skip: int = 0, # Pagination can be added later
    # limit: int = 20,
    repo: CustomerRepository = Depends(get_repo)
):
    business_id = 1
    if search:
        return await repo.search(search, business_id)
    return await repo.get_all(business_id)

@router.get("/{customer_id}", response_model=CustomerSchema)
async def get_customer(
    customer_id: int,
    repo: CustomerRepository = Depends(get_repo)
):
    business_id = 1
    customer = await repo.get_by_id(customer_id, business_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/", response_model=CustomerSchema)
async def create_customer(
    payload: CustomerCreate,
    repo: CustomerRepository = Depends(get_repo)
):
    business_id = 1
    
    # Check if duplicate (by phone or email if provided) - simplistic check
    if payload.phone:
        existing = await repo.get_by_phone(payload.phone, business_id)
        if existing:
             # For PWA, maybe we return the existing one or error?
             # Let's return existing for now to be safe, or error.
             # Error is safer.
             raise HTTPException(status_code=400, detail="Customer with this phone already exists")

    customer = Customer(
        business_id=business_id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        street=payload.street,
        city=payload.city,
        pipeline_stage=PipelineStage.NOT_CONTACTED
    )
    repo.add(customer)
    await repo.session.commit()
    await repo.session.refresh(customer)
    return customer
