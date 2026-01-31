from fastapi import APIRouter, HTTPException, Header, status
import os
import alembic.config
import alembic.command
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/migrate")
async def trigger_migration(
    x_admin_secret: str = Header(None),
):
    """
    Endpoint to manually trigger Alembic migrations.
    Protected by a secret header instead of Clerk auth.
    """
    expected_secret = os.environ.get("ADMIN_SECRET")
    if not expected_secret:
        # Fallback to CRON_SECRET if ADMIN_SECRET is not set, or just use a generic secret
        expected_secret = os.environ.get("CRON_SECRET")

    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Maintenance service misconfigured: ADMIN_SECRET or CRON_SECRET not set on server",
        )

    if x_admin_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin secret"
        )

    try:
        # Resolve absolute path to alembic.ini
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # This file is in src/api/v1/pwa/, alembic.ini is in project root
        project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
        alembic_ini_path = os.path.join(project_root, "alembic.ini")

        if not os.path.exists(alembic_ini_path):
            # Fallback check
            logger.warning(
                f"alembic.ini not found at {alembic_ini_path}, trying fallback"
            )
            project_root = os.getcwd()
            alembic_ini_path = os.path.join(project_root, "alembic.ini")

        if not os.path.exists(alembic_ini_path):
            raise FileNotFoundError(f"alembic.ini not found at {alembic_ini_path}")

        alembic_cfg = alembic.config.Config(alembic_ini_path)
        alembic.command.upgrade(alembic_cfg, "head")

        return {
            "status": "success",
            "message": "Migrations completed successfully",
        }
    except Exception as e:
        logger.error(f"Migration trigger failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}",
        )
