from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.crm_service import CRMService
from src.schemas.pwa import RequestSchema, RequestCreate, RequestUpdate
from src.models import User
from src.api.dependencies.clerk_auth import get_current_user

router = APIRouter()

async def get_crm_service(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CRMService:
    return CRMService(session, business_id=current_user.business_id)

@router.get("/", response_model=List[RequestSchema])
async def list_requests(
    search: Optional[str] = None,
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    min_date: Optional[datetime] = None,
    max_date: Optional[datetime] = None,
    service: CRMService = Depends(get_crm_service)
):
    requests = await service.request_repo.search(
        query=search or "all",
        business_id=service.business_id,
        status=status,
        urgency=urgency,
        min_date=min_date,
        max_date=max_date
    )
    return requests

@router.get("/{request_id}", response_model=RequestSchema)
async def get_request(
    request_id: int,
    service: CRMService = Depends(get_crm_service)
):
    request = await service.request_repo.get_by_id(request_id, service.business_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    return request

@router.post("/", response_model=RequestSchema)
async def create_request(
    data: RequestCreate,
    service: CRMService = Depends(get_crm_service)
):
    request = await service.create_request(
        description=data.description,
        customer_id=data.customer_id,
        urgency=data.urgency,
        expected_value=data.expected_value,
        items=[item.dict() for item in data.items] if data.items else None,
        follow_up_date=data.follow_up_date,
        customer_details=data.customer_details,
        subtotal=data.subtotal,
        tax_amount=data.tax_amount,
        tax_rate=data.tax_rate
    )
    return request

@router.patch("/{request_id}", response_model=RequestSchema)
async def update_request(
    request_id: int,
    data: RequestUpdate,
    service: CRMService = Depends(get_crm_service)
):
    try:
        request = await service.update_request(
            request_id=request_id,
            description=data.description,
            status=data.status,
            urgency=data.urgency,
            expected_value=data.expected_value,
            items=[item.dict() for item in data.items] if data.items is not None else None,
            follow_up_date=data.follow_up_date,
            customer_id=data.customer_id,
            subtotal=data.subtotal,
            tax_amount=data.tax_amount,
            tax_rate=data.tax_rate
        )
        return request
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{request_id}")
async def delete_request(
    request_id: int,
    service: CRMService = Depends(get_crm_service)
):
    request = await service.request_repo.get_by_id(request_id, service.business_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    await service.session.delete(request)
    await service.session.commit()
    return {"status": "success"}
