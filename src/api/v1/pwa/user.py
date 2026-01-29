from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession


from src.database import get_db
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User
from src.services.google_calendar_service import GoogleCalendarService

router = APIRouter()


@router.get("/integrations")
async def get_integrations(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Returns the status of all user integrations.
    """
    return {
        "google_calendar": {
            "connected": current_user.google_calendar_sync_enabled,
            "email": current_user.google_calendar_credentials.get("email")
            if current_user.google_calendar_credentials
            else None,
        }
    }


@router.get("/integrations/google-calendar/auth-url")
async def get_google_calendar_auth_url(
    success_url: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Generates a Google OAuth URL for the current user.
    """
    service = GoogleCalendarService()
    try:
        import json
        from typing import Any, Dict

        state_data: Dict[str, Any] = {"user_id": current_user.id}
        if success_url:
            state_data["success_url"] = success_url

        state = json.dumps(state_data)
        auth_url, _ = service.get_auth_url(state=state)
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/integrations/google-calendar")
async def disconnect_google_calendar(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """
    Disconnects Google Calendar for the current user.
    """
    current_user.google_calendar_sync_enabled = False
    current_user.google_calendar_credentials = None
    await db.commit()
    return {"status": "SUCCESS"}
