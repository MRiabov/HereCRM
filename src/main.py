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
    
    yield
    
    # Shutdown
    await messaging_service.stop()
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
