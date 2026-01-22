from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.database import engine, Base
from src.api.routes import router as webhook_router
from src.events import event_bus
from src.services.messaging_service import messaging_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Register Event Listeners
    app.state.event_bus = event_bus
    from src.services.pipeline_handlers import handle_job_created, handle_contact_event
    
    event_bus.subscribe("JOB_CREATED", handle_job_created)
    event_bus.subscribe("CONTACT_EVENT", handle_contact_event)
    
    # Register MessagingService event handlers
    messaging_service.register_handlers()
    
    # Start MessagingService background worker
    await messaging_service.start()

    # Start Scheduler Service
    from src.services.scheduler import scheduler_service
    # Schedule the daily shift check for 6:30 AM UTC
    scheduler_service.add_daily_job(scheduler_service.check_shifts, hour=6, minute=30)
    # Schedule the hourly QuickBooks sync
    scheduler_service.add_hourly_job(scheduler_service.run_hourly_quickbooks_sync)
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
from src.api.webhooks.stripe_webhook import router as stripe_router
app.include_router(stripe_router, prefix="/webhooks", tags=["webhooks"])


@app.get("/health")
def health_check():
    return {"status": "ok"}
