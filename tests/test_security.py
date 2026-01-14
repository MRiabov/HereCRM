import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.main import app
from src.security_utils import _rate_limit_data
from src.uimodels import ALLOWED_SETTING_KEYS
from src.models import Business, Customer
from src.repositories import CustomerRepository
from src.database import engine, Base
from src.api.routes import verify_signature

client = TestClient(app)


# Bypass signature verification for security tests
def bypass_verify_signature():
    return None


@pytest.fixture(autouse=True)
def setup_dependency_overrides():
    app.dependency_overrides[verify_signature] = bypass_verify_signature
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def clear_rate_limit():
    _rate_limit_data.clear()


@pytest.fixture
async def db_session():
    from src.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


@pytest.mark.asyncio
async def test_rate_limiting():
    """Verify that requests are limited after a threshold."""
    payload = {"from_number": "+1234567890", "body": "Hello"}

    # 10 requests allowed
    for _ in range(10):
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["reply"] != "Too many requests. Please try again later."

    # 11th request should be limited
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json()["reply"] == "Too many requests. Please try again later."


@pytest.mark.asyncio
async def test_input_length_validation():
    """Verify that excessively long inputs are rejected by Pydantic."""
    long_body = "A" * 1001
    payload = {"from_number": "+1234567890", "body": long_body}

    response = client.post("/webhook", json=payload)
    # 422 Unprocessable Entity because of Pydantic validation on the model
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_phone_format():
    """Verify that invalid phone formats are rejected."""
    payload = {"from_number": "invalid-phone", "body": "Hello"}

    response = client.post("/webhook", json=payload)
    assert response.status_code == 422


def test_settings_allowlist():
    """Verify only allowed setting keys can be updated."""
    from src.uimodels import UpdateSettingsTool

    try:
        from pydantic.v1 import ValidationError
    except ImportError:
        from pydantic import ValidationError

    # Valid key
    tool = UpdateSettingsTool(setting_key=ALLOWED_SETTING_KEYS[0], setting_value="test")
    assert tool.setting_key == ALLOWED_SETTING_KEYS[0]

    # Invalid key
    with pytest.raises(ValidationError):
        UpdateSettingsTool(setting_key="malicious_key", setting_value="hack")


@pytest.mark.asyncio
async def test_tenant_isolation_repository(db_session):
    """Verify that repositories correctly scope queries to business_id."""
    # Setup two businesses
    b1 = Business(name="Biz 1")
    b2 = Business(name="Biz 2")
    db_session.add(b1)
    db_session.add(b2)
    await db_session.flush()

    c1 = Customer(name="John Biz 1", business_id=b1.id)
    c2 = Customer(name="John Biz 2", business_id=b2.id)
    db_session.add(c1)
    db_session.add(c2)
    await db_session.commit()

    repo = CustomerRepository(db_session)

    # Search in Biz 1
    results = await repo.search("John", b1.id)
    assert len(results) == 1
    assert results[0].name == "John Biz 1"
    assert results[0].business_id == b1.id

    # Search in Biz 2
    results = await repo.search("John", b2.id)
    assert len(results) == 1
    assert results[0].name == "John Biz 2"
    assert results[0].business_id == b2.id


@pytest.mark.asyncio
async def test_sql_injection_mitigation(db_session):
    """Verify that SQL injection patterns are treated as literal strings and not executed."""
    b1 = Business(name="Biz 1")
    db_session.add(b1)
    await db_session.flush()

    c1 = Customer(name="Normal User", business_id=b1.id)
    db_session.add(c1)
    await db_session.commit()

    repo = CustomerRepository(db_session)

    # Attempt standard SQL injection
    injection_query = "' OR '1'='1"
    results = await repo.search(injection_query, b1.id)

    # Should return empty list, not all customers
    assert len(results) == 0


def test_llm_instruction_hardening():
    """Verify that LLMParser has security hardening in its system instructions."""
    from src.llm_client import LLMParser

    with patch("google.genai.configure"):
        with patch("google.genai.GenerativeModel"):
            parser = LLMParser()
            instr = parser.system_instruction.lower()
            assert "ignore" in instr
            assert "override" in instr
            assert "security" in instr or "critical" in instr
            assert "disclose" in instr or "reveal" in instr
