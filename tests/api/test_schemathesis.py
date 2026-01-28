import schemathesis
from src.main import app
from src.api.dependencies.clerk_auth import verify_token, get_current_user
from src.database import engine
from src.models import Base, User, Business, UserRole
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
import pytest
import asyncio
from hypothesis import settings, HealthCheck
import src.utils.schema_validation

# Monkeypatch schema validation to skip it during schemathesis tests
src.utils.schema_validation.validate_db_schema = lambda: []

# --- DB Setup ---

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        biz = Business(id=1, name="Test Business")
        session.add(biz)
        await session.flush()
        
        user = User(
            id=1,
            clerk_id="user_2p8I7U3N7rW1z9P0Q2oW3m4n5k6",
            name="Test User",
            email="test@example.com",
            business_id=biz.id,
            role=UserRole.OWNER
        )
        session.add(user)
        await session.commit()

# Initialize DB once per session
@pytest.fixture(scope="session", autouse=True)
def db_init(event_loop):
    event_loop.run_until_complete(setup_test_db())
    yield
    # No need to drop if it's in-memory and session ends

# --- Mocks ---

async def mock_user():
    return User(
        id=1,
        clerk_id="user_2p8I7U3N7rW1z9P0Q2oW3m4n5k6",
        name="Test User",
        email="test@example.com",
        business_id=1,
        role=UserRole.OWNER
    )

app.dependency_overrides[verify_token] = mock_user
app.dependency_overrides[get_current_user] = mock_user

# --- Schemathesis Setup ---
import json
import os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "../../herecrm-pwa-openapi.json")

if os.path.exists(SCHEMA_PATH):
    with open(SCHEMA_PATH, "r") as f:
        raw_schema = json.load(f)
    schema = schemathesis.openapi.from_dict(raw_schema)
    schema.app = app
    schema.base_url = "http://localhost/api/v1"
else:
    schema = schemathesis.openapi.from_asgi("/openapi.json", app)

@pytest.mark.schemathesis
@schema.include(path_regex="^/api/v1/pwa/").parametrize()
@settings(
    max_examples=1, # Smoke test mode for CI/CD
    deadline=None,
    suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow]
)
def test_pwa_api_schema(case):
    response = case.call()
    case.validate_response(response)