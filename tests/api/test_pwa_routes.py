import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, patch
from datetime import date, datetime, timezone

from src.main import app
from src.database import get_db, Base
from src.models import Business, User, UserRole, Customer, Job, PipelineStage, Message, MessageRole, Invoice

# Setup In-Memory DB
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    bind=engine_test, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture
async def db_session():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        # Seed required data (Business, User)
        biz = Business(name="Test Biz", id=1)
        session.add(biz)
        user = User(
            name="Test User", 
            email="test@example.com", 
            phone_number="+1234567890",
            business_id=1,
            role=UserRole.OWNER
        )
        session.add(user)
        await session.commit()
        yield session

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
def override_get_db():
    async def _override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

@pytest.mark.asyncio
async def test_dashboard_stats(db_session, override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/pwa/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert "revenue_monthly" in data
        assert "active_leads_count" in data
        assert "pipeline_breakdown" in data

@pytest.mark.asyncio
async def test_jobs_e2e(db_session, override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create Customer
        cust_payload = {"name": "Test Customer", "phone": "+1999888777"}
        resp = await ac.post("/api/v1/pwa/customers/", json=cust_payload)
        assert resp.status_code == 200
        customer_id = resp.json()["id"]

        # 2. Create Job
        job_payload = {
            "customer_id": customer_id,
            "description": "Fix roof",
            "status": "scheduled",
            "scheduled_at": datetime.now(timezone.utc).isoformat(),
            "value": 500.0,
            "location": "123 Street"
        }
        resp = await ac.post("/api/v1/pwa/jobs/", json=job_payload)
        assert resp.status_code == 200
        job_id = resp.json()["id"]
        assert resp.json()["description"] == "Fix roof"

        # 3. List Jobs
        today = date.today().isoformat()
        resp = await ac.get(f"/api/v1/pwa/jobs/?date_from={today}")
        assert resp.status_code == 200
        jobs = resp.json()
        # Note: DashboardService might filter by assigned employee. 
        # In this test we didn't assign an employee to the job unless create_job does it (it doesn't by default).
        # And DashboardService logic for "get_employee_schedules" only returns jobs assigned to employees.
        # So this might return empty if no employee assigned.
        # Let's check logic: Jobs endpoint calls dashboard.get_employee_schedules.
        # That function queries jobs where employee_id IN [list of employees].
        # Our job has employee_id=None.
        # So it might not show up.
        
        # We should update the job to assign an employee.
        # First get the user id (seeded as 1).
        
        # 4. Update Job to assign employee
        update_payload = {"employee_id": 1} # Assuming User ID 1 exists from fixture
        # Wait, the fixture creates User, but we don't know ID for sure? 
        # usually autoincrement starts at 1, but let's query.
        # Currently we can't query easily inside test unless we use session.
        # But we know ID=1 because we set it explicitly in fixture? No, we set Business ID=1.
        # Let's set User ID=1 explicitly in fixture just to be safe.
        # (Updating fixture above in thought process, and writing it in code)
        
        # Actually User(id=1, ...) in fixture would be better.
        # But let's fetch it via another endpoint or assume.
        # Or just use the session passed to test.
        from sqlalchemy import select
        res = await db_session.execute(select(User))
        user = res.scalars().first()
        user_id = user.id
        
        update_payload = {"employee_id": user_id}
        resp = await ac.patch(f"/api/v1/pwa/jobs/{job_id}", json=update_payload)
        assert resp.status_code == 200
        
        # Now list again
        resp = await ac.get(f"/api/v1/pwa/jobs/?date_from={today}")
        assert resp.status_code == 200
        jobs = resp.json()
        # Should be there now
        assert len(jobs) >= 1
        assert jobs[0]["id"] == job_id

@pytest.mark.asyncio
async def test_chat_send(db_session, override_get_db):
    # Mock messaging service
    with patch("src.api.v1.pwa.chat.messaging_service.send_message", new_callable=AsyncMock) as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Create Customer First
            cust_payload = {"name": "Chatter", "phone": "+1555000111"}
            resp = await ac.post("/api/v1/pwa/customers/", json=cust_payload)
            customer_id = resp.json()["id"]

            payload = {
                "customer_id": customer_id,
                "message": "Hello PWA"
            }
            resp = await ac.post("/api/v1/pwa/chat/send", json=payload)
            assert resp.status_code == 200
            
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            assert kwargs["recipient_phone"] == "+1555000111"
            assert kwargs["content"] == "Hello PWA"

@pytest.mark.asyncio
async def test_invoices_list(db_session, override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Setup data: Customer -> Job -> Invoice
        cust = Customer(name="Invoice Customer", business_id=1)
        db_session.add(cust)
        await db_session.flush()
        
        job = Job(business_id=1, customer_id=cust.id, value=150.0, description="Inv Job")
        db_session.add(job)
        await db_session.flush()
        
        inv = Invoice(job_id=job.id, s3_key="k", public_url="u", payment_link="l")
        db_session.add(inv)
        await db_session.commit()
        
        resp = await ac.get("/api/v1/pwa/invoices/")
        assert resp.status_code == 200
        invoices = resp.json()
        assert len(invoices) >= 1
        assert invoices[0]["total_amount"] == 150.0
        assert invoices[0]["customer_name"] == "Invoice Customer"

