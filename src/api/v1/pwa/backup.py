from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.data_management import DataManagementService
import os

router = APIRouter()


async def get_data_service(
    session: AsyncSession = Depends(get_db),
) -> DataManagementService:
    return DataManagementService(session)


@router.post("/trigger")
async def trigger_backup(
    x_cron_secret: str = Header(None),
    service: DataManagementService = Depends(get_data_service),
):
    """
    Endpoint for automated backups.
    Protected by a secret header instead of Clerk auth.
    """
    expected_secret = os.environ.get("CRON_SECRET")
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backup service misconfigured: CRON_SECRET not set on server",
        )

    if x_cron_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret"
        )

    try:
        backup_url = await service.backup_db()
        return {
            "status": "success",
            "message": "Database backup completed successfully",
            "backup_url": backup_url,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup failed: {str(e)}",
        )
