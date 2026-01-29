from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from src.database import get_db
from src.services.data_management import DataManagementService
from src.schemas.pwa import ExportRequestSchema, DataActivitySchema, ExportCreateRequest
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, ImportJob, ExportRequest

router = APIRouter()


async def get_data_service(
    session: AsyncSession = Depends(get_db),
) -> DataManagementService:
    return DataManagementService(session)


@router.post("/export", response_model=ExportRequestSchema)
async def trigger_export(
    payload: ExportCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    service: DataManagementService = Depends(get_data_service),
):
    # DataManagementService.export_data is currently sync-ish (S3 upload might be blocking)
    # Actually it's async. We can run it directly or in background.
    # The service method itself commits to DB.

    # We'll normalize format to lowercase as expected by service
    export_format = payload.format.lower()
    if export_format == "xlsx":
        export_format = "excel"

    # We'll trigger it directly for now since it's already async and handles its own status
    query_text = payload.query or ""

    export_req = await service.export_data(
        business_id=current_user.business_id, query=query_text, format=export_format
    )

    return export_req


@router.get("/activity", response_model=DataActivitySchema)
async def get_data_activity(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    # Fetch recent imports and exports
    import_stmt = (
        select(ImportJob)
        .where(ImportJob.business_id == current_user.business_id)
        .order_by(desc(ImportJob.created_at))
        .limit(10)
    )
    export_stmt = (
        select(ExportRequest)
        .where(ExportRequest.business_id == current_user.business_id)
        .order_by(desc(ExportRequest.created_at))
        .limit(10)
    )

    import_result = await db.execute(import_stmt)
    export_result = await db.execute(export_stmt)

    return DataActivitySchema(
        imports=import_result.scalars().all(), exports=export_result.scalars().all()
    )
