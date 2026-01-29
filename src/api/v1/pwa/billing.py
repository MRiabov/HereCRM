from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from src.database import get_db
from src.services.billing_service import BillingService
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, UserRole
from pydantic import BaseModel, Field

router = APIRouter()


class CheckoutSessionRequest(BaseModel):
    item_type: str = Field(..., pattern="^(seat|messaging|addon)$", max_length=20)
    item_id: Optional[str] = Field(None, max_length=50)
    success_url: str = Field(..., max_length=500)
    cancel_url: str = Field(..., max_length=500)


async def get_billing_service(
    session: AsyncSession = Depends(get_db),
) -> BillingService:
    return BillingService(session)


@router.get("/prices")
async def get_billing_prices(
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
):
    """Exposes billing configuration (prices, products, addons) to the frontend."""
    return service.config


@router.post("/checkout")
async def create_checkout_session(
    request: CheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    service: BillingService = Depends(get_billing_service),
):
    """Creates a Stripe checkout session for a specific upgrade."""
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403, detail="Only owners can initiate billing changes"
        )

    try:
        result = await service.create_upgrade_link(
            business_id=current_user.business_id,
            item_type=request.item_type,
            item_id=request.item_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to create checkout session")
