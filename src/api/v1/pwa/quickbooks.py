from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, UserRole
from src.services.accounting.quickbooks_auth import QuickBooksAuthService
from src.services.accounting.service import AccountingService

router = APIRouter()


async def get_auth_service(
    session: AsyncSession = Depends(get_db),
) -> QuickBooksAuthService:
    return QuickBooksAuthService(session)


async def get_accounting_service(
    session: AsyncSession = Depends(get_db),
) -> AccountingService:
    return AccountingService(session)


@router.get("/connect")
async def connect_quickbooks(
    current_user: User = Depends(get_current_user),
    auth_service: QuickBooksAuthService = Depends(get_auth_service),
):
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403, detail="Only owners can connect QuickBooks"
        )

    url = auth_service.generate_auth_url(current_user.business_id)
    return {"url": url}


@router.get("/callback")
async def quickbooks_callback(
    code: str,
    realmId: str,
    state: str,
    auth_service: QuickBooksAuthService = Depends(get_auth_service),
):
    # state contains business_id and csrf token
    try:
        await auth_service.handle_callback(code, realmId, state)
    except Exception:
        # Redirect with error or show error page
        # For now, redirect back to PWA with error param
        return RedirectResponse(url="/settings/workflow?qb_error=true")

    # Redirect back to workflow settings in PWA
    return RedirectResponse(url="/settings/workflow?qb_success=true")


@router.post("/disconnect")
async def disconnect_quickbooks(
    current_user: User = Depends(get_current_user),
    auth_service: QuickBooksAuthService = Depends(get_auth_service),
):
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=403, detail="Only owners can disconnect QuickBooks"
        )

    await auth_service.disconnect(current_user.business_id)
    return {"status": "SUCCESS"}


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_user),
    accounting_service: AccountingService = Depends(get_accounting_service),
):
    if current_user.role != UserRole.OWNER:
        raise HTTPException(status_code=403, detail="Only owners can trigger sync")

    await accounting_service.trigger_manual_sync(current_user.business_id)
    return {"status": "SUCCESS"}
