from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import traceback
from src.config import settings
from src.database import engine, Base
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
    # if ":memory:" not in str(engine.url):
    #     logger = logging.getLogger("src.main")
    #     logger.info("Running database migrations...")
    #     try:
    #         import alembic.config
    #         import alembic.command

    #         alembic_cfg = alembic.config.Config("alembic.ini")
    #         # Ensure we are in the correct directory for alembic.ini if needed,
    #         # but usually it's in the root
    #         alembic.command.upgrade(alembic_cfg, "head")
    #         logger.info("Migrations completed successfully.")
    #     except Exception as e:
    #         logger.error(f"Failed to run migrations: {e}")
    #         # Continue anyway, as validation might still pass if it was already at head

    # Startup: Create tables (as a fallback/for new tables not in migrations yet)
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)

    # Force-check schema consistency - SKIP for in-memory database as validation uses a separate connection
    # if ":memory:" not in str(engine.url):
    #     from src.utils.schema_validation import validate_db_schema

    #     mismatches = validate_db_schema()
    #     if mismatches:
    #         # Filter out minor things or handle specific cases if needed
    #         # For now, we throw on ANY mismatch to ensure dev discipline
    #         error_msg = f"Database schema mismatch detected: {mismatches}"
    #         logger_for_mismatch = logging.getLogger("src.main")
    #         logger_for_mismatch.error(error_msg)
    #         raise RuntimeError(error_msg)
    # else:
    #     logging.getLogger("src.main").info(
    #         "Skipping schema validation for in-memory database"
    #     )

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
    scheduler_service.stop()
    await automation_service.stop()
    await messaging_service.stop()
    from src.services.geocoding import GeocodingService

    await GeocodingService.close_client()
    from src.api.v1.pwa.analytics_proxy import close_client as close_analytics_client

    await close_analytics_client()
    await engine.dispose()


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
