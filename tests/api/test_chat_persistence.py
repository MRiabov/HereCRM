import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.api.dependencies.clerk_auth import get_current_user
from src.models import User, MessageRole
from sqlalchemy import select


# Mock User
class MockUser:
    id = 1
    business_id = 1
    role = "OWNER"
    name = "Test User"
    phone_number = "+15550000"


@pytest.fixture
async def client():
    from src.api.dependencies.clerk_auth import verify_token
    from src.database import AsyncSessionLocal
    from src.models import Business, UserRole

    # Create records in DB
    async with AsyncSessionLocal() as db:
        # Check if business exists
        stmt = select(Business).where(Business.id == 1)
        res = await db.execute(stmt)
        business = res.scalar_one_or_none()
        if not business:
            business = Business(id=1, name="Test Business")
            db.add(business)
            await db.flush()

        # Check if user exists
        stmt = select(User).where(User.id == 1)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                id=1,
                business_id=1,
                role=UserRole.OWNER,
                name="Test User",
                phone_number="+15550000",
                clerk_id="test_clerk_id",
            )
            db.add(user)
        await db.commit()

    async def mock_auth_bypass():
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(User).where(User.id == 1))
            return res.scalar_one()

    app.dependency_overrides[verify_token] = mock_auth_bypass
    app.dependency_overrides[get_current_user] = mock_auth_bypass

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer mock-token"},
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_ai_chat_persistence(client):
    from unittest.mock import patch, AsyncMock
    from src.uimodels import AddJobTool

    # 1. Send message to AI - should return 'proposed'
    payload = {"customer_id": 0, "message": "Add job for Bob, $100"}

    mock_tool = AddJobTool(customer_name="Bob", price=100.0, description="Clean house")

    with patch(
        "src.api.v1.pwa.chat.parser.parse", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = mock_tool

        response = await client.post("/api/v1/pwa/chat/send", json=payload)
        assert response.status_code == 200
        data = response.json()
        # The API now returns status="SENT" but the content is the JSON string of the proposal
        assert data["status"] == "SENT"

        import json

        proposal = json.loads(data["content"])
        assert proposal["status"] == "proposed"
        assert proposal["tool"] == "AddJobTool"

        # 2. Execute the tool
        exec_payload = {"tool_name": "AddJobTool", "arguments": proposal["data"]}
        exec_response = await client.post("/api/v1/pwa/chat/execute", json=exec_payload)
        assert exec_response.status_code == 200
        exec_data = exec_response.json()
        assert exec_data["status"] == "SENT"
        assert exec_data["is_executed"] is True

    # 3. Check history
    history_res = await client.get("/api/v1/pwa/chat/history/0")
    assert history_res.status_code == 200
    history = history_res.json()

    # Should find the draft message and verify it is marked as executed
    draft_msg = next(
        (m for m in history if '"status": "proposed"' in m["content"]), None
    )
    assert draft_msg is not None
    assert draft_msg["is_executed"] is True

    # Should have: user request, and AI response (after execution)
    # The proposal itself is NOT strictly required in history if PWA handles it via cards,
    # but the current logic saves it as a message.
    # Actually, send_message logs the user message. execute_tool logs the assistant message.
    assert len(history) >= 2
    assert history[0]["content"] == "Add job for Bob, $100"
    assert history[0]["role"] == MessageRole.USER
    assert history[1]["role"] == MessageRole.ASSISTANT


@pytest.mark.asyncio
async def test_strict_ai_logic_no_tool(client):
    from unittest.mock import AsyncMock, patch
    from src.uimodels import HelpTool

    # Send non-tool message
    payload = {"customer_id": 0, "message": "How are you today?"}

    with patch(
        "src.api.v1.pwa.chat.parser.parse", new_callable=AsyncMock
    ) as mock_parse, patch(
        "src.llm_client.LLMParser.chat_completion", new_callable=AsyncMock
    ) as mock_chat_completion:
        mock_parse.return_value = HelpTool(query="How are you today?")
        mock_chat_completion.side_effect = Exception("OpenRouter unavailable")

        response = await client.post("/api/v1/pwa/chat/send", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SENT"
    assert "help" in data["content"].lower() or "assist" in data["content"].lower()


@pytest.mark.asyncio
async def test_customer_chat_persistence(client):
    # Create a customer first
    customer_data = {"name": "Persist Customer", "phone": "+15559999"}
    cust_res = await client.post("/api/v1/pwa/customers/", json=customer_data)
    assert cust_res.status_code == 200
    customer_id = cust_res.json()["id"]

    # Send message to customer
    payload = {"customer_id": customer_id, "message": "See you at 10am!"}
    response = await client.post("/api/v1/pwa/chat/send", json=payload)
    assert response.status_code == 200

    # Check history
    history_res = await client.get(f"/api/v1/pwa/chat/history/{customer_id}")
    assert history_res.status_code == 200
    history = history_res.json()

    # Check if both user message and outbound were saved (per my new logic)
    # Actually my logic saves two messages: one from technician, one 'system' to customer
    assert len(history) >= 2
    assert history[0]["content"] == "See you at 10am!"
    assert history[0]["role"] == MessageRole.USER
    assert history[1]["content"] == "See you at 10am!"
    assert history[1]["role"] == MessageRole.ASSISTANT
