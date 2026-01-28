from fastapi import APIRouter, Depends, HTTPException, status

from pydantic import BaseModel, Field
from typing import Optional

from src.api.dependencies.auth import get_api_key_auth
from src.models import IntegrationConfig, IntegrationType, Customer, Request
from src.repositories import CustomerRepository, RequestRepository
from src.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from src.utils.security import Signer
from src.config import settings

router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

class ProvisionRequest(BaseModel):
    auth_id: str = Field(..., max_length=100)
    config_type: str = Field(..., max_length=50)  # INBOUND_KEY, META_CAPI, WEBHOOK
    label: str = Field(..., max_length=100)
    payload: dict

class LeadRequest(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    source: Optional[str] = Field("api", max_length=50)

class ServiceRequest(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = Field(None, max_length=255)
    service_type: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)

@router.post("/provision", status_code=status.HTTP_201_CREATED)

async def provision_integration(
    payload: ProvisionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Provisioning endpoint to save integration credentials.
    Protected by auth_id signature validation.
    """
    # Verify provisioning signature
    # In a real app, the server signs a token for the UI.
    # Here we verify the config_type + label was signed by our secret.
    is_valid = Signer.verify(payload.config_type + payload.label, payload.auth_id, settings.secret_key)
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid provisioning signature")

    try:
        config_type = IntegrationType[payload.config_type]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid config_type")

    # Business ID must be handled. For this implementation, we expect it in the payload.
    business_id = payload.payload.get("business_id")
    if not business_id:
         raise HTTPException(status_code=400, detail="business_id is required in payload")

    config = IntegrationConfig(
        business_id=business_id,
        type=config_type,
        label=payload.label,
        config_payload=payload.payload,
        is_active=True
    )
    
    db.add(config)
    await db.commit()
    return {"status": "success", "config_id": str(config.id)}

@router.post("/leads", status_code=status.HTTP_201_CREATED)

async def create_lead(
    payload: LeadRequest,
    config: IntegrationConfig = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest leads from external systems.
    """
    business_id = config.business_id
    customer_repo = CustomerRepository(db)
    
    # Deduplicate by phone
    customer = await customer_repo.get_by_phone(payload.phone, business_id)
    is_existing = True
    if not customer:
        is_existing = False
        customer = Customer(
            business_id=business_id,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            details=f"Source: {payload.source}"
        )
        customer_repo.add(customer)
        await db.flush()
    
    await db.commit()
    return {"customer_id": customer.id, "is_existing": is_existing}

@router.post("/requests", status_code=status.HTTP_201_CREATED)

async def create_request(
    payload: ServiceRequest,
    config: IntegrationConfig = Depends(get_api_key_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest service requests.
    """
    business_id = config.business_id
    customer_repo = CustomerRepository(db)
    request_repo = RequestRepository(db)
    
    # 1. Find or create customer
    customer = await customer_repo.get_by_phone(payload.phone, business_id)
    if not customer:
        customer = Customer(
            business_id=business_id,
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            street=payload.address
        )
        customer_repo.add(customer)
        await db.flush()
    
    # 2. Create Request
    # Request model has business_id and description
    content = f"Service: {payload.service_type or 'General'}\n"
    content += f"Address: {payload.address or 'N/A'}\n"
    content += f"Notes: {payload.notes or 'N/A'}\n"
    # Link customer info in description since model might not have customer_id or we want to keep it simple
    full_content = f"Lead: {customer.name} ({customer.phone})\n{content}"
    
    request = Request(
        business_id=business_id,
        description=full_content,
        status="PENDING"
    )
    request_repo.add(request)
    await db.commit()
    
    return {"request_id": request.id, "customer_id": customer.id}
