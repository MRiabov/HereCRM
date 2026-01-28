from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import joinedload

from src.database import get_db
from src.models import Customer, Job, User
from src.api.dependencies.clerk_auth import get_current_user
from src.schemas.pwa import AddressSearchResult, AddressSearchType

router = APIRouter()



@router.get("/", response_model=List[AddressSearchResult])
async def search_addresses(
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not search or len(search) < 2:
        return []

    results = []
    
    # 1. Search customers by address fields
    customer_stmt = (
        select(Customer)
        .where(
            Customer.business_id == current_user.business_id,
            or_(
                Customer.street.ilike(f"%{search}%"),
                Customer.city.ilike(f"%{search}%"),
                Customer.original_address_input.ilike(f"%{search}%")
            )
        )
    )
    customer_res = await session.execute(customer_stmt)
    for c in customer_res.scalars().all():
        addr = c.street or c.original_address_input or c.city
        if addr:
            results.append(AddressSearchResult(
                id=c.id,
                address=addr,
                customer=c.name or "Unknown",
                type=AddressSearchType.CUSTOMER
            ))

    # 2. Search jobs by location
    job_stmt = (
        select(Job)
        .join(Customer)
        .where(
            Job.business_id == current_user.business_id,
            Job.location.ilike(f"%{search}%")
        )
        .options(joinedload(Job.customer))
    )
    job_res = await session.execute(job_stmt)
    for j in job_res.scalars().all():
        if j.location:
            results.append(AddressSearchResult(
                id=j.id,
                address=j.location,
                customer=j.customer.name if j.customer else "Unknown",
                type=AddressSearchType.JOB
            ))

    # Deduplicate by address + customer
    seen = set()
    unique_results = []
    for r in results:
        key = (r.address.lower(), (r.customer or "").lower())
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results[:20]
