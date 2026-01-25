from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.database import engine, Base
from src.api.routes import router as webhook_router
from src.api.webhooks.stripe_webhook import router as stripe_router
from src.api.v1.integrations import router as integrations_v1
from src.api.v1.pwa.router import router as pwa_router
from src.events import event_bus
from src.services.messaging_service import messaging_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Register Event Listeners
    app.state.event_bus = event_bus
    # Import handlers to register them via decorators
    import src.services.pipeline_handlers  # noqa: F401
    import src.handlers.integration_handlers  # noqa: F401
    import src.handlers.automation_handlers  # noqa: F401
    
    # Register MessagingService event handlers
    messaging_service.register_handlers()

    # Register CalendarSyncHandler event handlers
    from src.services.calendar_sync_handler import calendar_sync_handler
    calendar_sync_handler.register()
    
    # Start MessagingService background worker
    await messaging_service.start()

    # Start Scheduler Service
    from src.services.scheduler import scheduler_service
    # Schedule the daily shift check for 6:30 AM UTC
    scheduler_service.add_daily_job(scheduler_service.check_shifts, hour=6, minute=30)
    scheduler_service.start()
    
    yield
    
    # Shutdown
    scheduler_service.stop()
    await messaging_service.stop()
    from src.services.geocoding import GeocodingService
    await GeocodingService.close_client()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router)
app.include_router(stripe_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(integrations_v1)

app.include_router(pwa_router, prefix="/api/v1/pwa")


@app.get("/health")
def health_check():
    return {"status": "ok"}
