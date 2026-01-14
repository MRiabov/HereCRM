from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.database import engine, Base
from src.api.routes import router as webhook_router
from src.events import event_bus


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    app.state.event_bus = event_bus
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
