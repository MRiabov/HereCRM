import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
import os
from src.config import settings
from src.database import engine, Base, repair_sqlite_schema
from src.api.routes import router as webhook_router
from src.api.webhooks.stripe_webhook import router as stripe_router
from src.api.webhooks.clerk import router as clerk_router
from src.api.v1.integrations import router as integrations_v1
from src.api.v1.pwa.router import router as pwa_router
from src.events import event_bus
from src.services.messaging_service import messaging_service
from src.services.automation_service import automation_service
from src.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging configuration
    setup_logging()

    # Run migrations automatically
    if settings.automigrate:
        if ":memory:" not in str(engine.url):
            logger = logging.getLogger("src.main")
            logger.info("Running database migrations...")
            try:
                import alembic.config
                import alembic.command

                # Resolve absolute path to alembic.ini
                # This file is in src/, alembic.ini is in the parent directory
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(current_dir)
                alembic_ini_path = os.path.join(project_root, "alembic.ini")

                alembic_cfg = alembic.config.Config(alembic_ini_path)
                alembic.command.upgrade(alembic_cfg, "head")
                logger.info("Migrations completed successfully.")
            except Exception as e:
                logger.error(f"Failed to run migrations: {e}")

        # Startup: Create tables (as a fallback/for new tables not in migrations yet)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # SQLite deployments can drift when a refactor lands before the live DB is migrated.
    # Repair missing columns after migrations so the app can boot against an older volume.
    if ":memory:" not in str(engine.url) and getattr(engine.dialect, "name", "") == "sqlite":
        repaired_columns = await repair_sqlite_schema()
        if repaired_columns:
            logger = logging.getLogger("src.main")
            logger.info(
                "Repaired SQLite schema columns: %s",
                ", ".join(f"{table}.{column}" for table, column in repaired_columns),
            )

    # Force-check schema consistency - SKIP for in-memory database as validation uses a separate connection
    if settings.automigrate:
        if ":memory:" not in str(engine.url):
            from src.utils.schema_validation import validate_db_schema

            mismatches = validate_db_schema()
            if mismatches:
                # Filter out minor things or handle specific cases if needed
                # For now, we throw on ANY mismatch to ensure dev discipline
                error_msg = f"Database schema mismatch detected: {mismatches}"
                logger_for_mismatch = logging.getLogger("src.main")
                logger_for_mismatch.error(error_msg)

                if os.getenv("SKIP_SCHEMA_VALIDATION") == "true":
                    logger_for_mismatch.warning(
                        "!!! WARNING: SKIP_SCHEMA_VALIDATION is enabled. Proceeding with mismatching schema !!!"
                    )
                else:
                    raise RuntimeError(error_msg)
        else:
            logging.getLogger("src.main").info(
                "Skipping schema validation for in-memory database"
            )

    # Register Event Listeners
    app.state.event_bus = event_bus
    # Import handlers to register them via decorators
    import src.services.pipeline_handlers  # noqa: F401
    import src.handlers.integration_handlers  # noqa: F401

    # Register Event Handlers
    messaging_service.register_handlers()
    automation_service.register_handlers()

    # Register CalendarSyncHandler event handlers
    from src.services.calendar_sync_handler import calendar_sync_handler

    calendar_sync_handler.register()

    # Start background workers
    await messaging_service.start()
    await automation_service.start()

    # Start Scheduler Service
    from src.services.scheduler import scheduler_service

    # Schedule the daily shift check for 6:30 AM UTC
    scheduler_service.add_daily_job(scheduler_service.check_shifts, hour=6, minute=30)
    scheduler_service.start()

    yield

    # Shutdown
    async def shutdown_all():
        await scheduler_service.stop()
        await automation_service.stop()
        await messaging_service.stop()
        from src.services.geocoding import GeocodingService

        await GeocodingService.close_client()
        from src.api.v1.pwa.analytics_proxy import (
            close_client as close_analytics_client,
        )

        await close_analytics_client()
        await engine.dispose()

    try:
        # Fallback timeout to ensure the process always exits during dev reload/shutdown
        await asyncio.wait_for(shutdown_all(), timeout=5.0)
    except asyncio.TimeoutError:
        logger = logging.getLogger("src.main")
        logger.warning("Lifespan shutdown timed out after 5 seconds")
    except Exception as e:
        logger = logging.getLogger("src.main")
        logger.error(f"Error during lifespan shutdown: {e}")


app = FastAPI(lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BackendErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            if settings.dev_mode:
                # Capture error for test introspection
                if not hasattr(request.app.state, "backend_errors"):
                    request.app.state.backend_errors = []

                error_detail = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                request.app.state.backend_errors.append(error_detail)

                # Keep the list manageable
                if len(request.app.state.backend_errors) > 50:
                    request.app.state.backend_errors.pop(0)

            # Re-raise to let FastAPI handle the 500 response/logging as usual
            raise e


if settings.dev_mode:
    app.add_middleware(BackendErrorMiddleware)

app.include_router(webhook_router)
app.include_router(stripe_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(clerk_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(integrations_v1)

app.include_router(pwa_router, prefix="/api/v1/pwa")


@app.get("/health")
def health_check():
    return {"status": "ok"}
