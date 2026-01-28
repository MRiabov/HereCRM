
import os
import pytest
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///test_customer_pov.db"

from src.main import app
from src.database import engine
from src.models import Business, User, Customer, Job, UserRole, PipelineStage
from src.services.messaging_service import messaging_service

@pytest.mark.asyncio
async def test_customer_pov_scenarios():
    # 1. Setup Data
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with engine.begin() as conn:
            from src.models import Base
            await conn.run_sync(Base.metadata.create_all)

        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with SessionLocal() as db:
            biz = Business(name="Happy Plumb")
            db.add(biz)
            await db.flush()
            
            # Pre-create User records to avoid "is_new_user" onboarding flow in tests
            owner_user = User(phone_number="+111222333", business_id=biz.id, role=UserRole.OWNER, name="Owner Bob")
            tech_user = User(
                phone_number="+444555666", 
                business_id=biz.id, 
                role=UserRole.EMPLOYEE, 
                name="Tech Tom",
                current_latitude=53.3501,
                current_longitude=-6.2661,
                location_updated_at=datetime.now(timezone.utc)
            )
            cust_user = User(phone_number="+777888999", business_id=biz.id, role=UserRole.MANAGER, name="Alice User")
            db.add(owner_user)
            db.add(tech_user)
            db.add(cust_user)
            
            customer = Customer(name="Alice Customer", phone="+777888999", business_id=biz.id, pipeline_stage=PipelineStage.CONTACTED)
            db.add(customer)
            await db.flush()
            
            job = Job(
                business_id=biz.id,
                customer_id=customer.id,
                description="Fix Leak",
                status="SCHEDULED",
                scheduled_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                employee_id=tech_user.id,
                latitude=53.3498, # Dublin
                longitude=-6.2603
            )
            db.add(job)
            await db.commit()

        # Mocking external services
        with (
            patch("src.llm_client.parser.parse", new_callable=AsyncMock) as mock_parser,
            patch("src.services.messaging_service.MessagingService.send_message", new_callable=AsyncMock) as mock_send,
            patch("src.services.messaging_service.MessagingService.enqueue_message", new_callable=AsyncMock) as mock_enqueue,
            patch("src.services.routing.ors.OpenRouteServiceAdapter.get_eta_minutes") as mock_eta,
            patch("src.services.location_service.LocationService.get_employee_location") as mock_loc,
        ):
            # Register handlers manually because conftest resets event_bus
            messaging_service.register_handlers()
            
            mock_send.return_value = AsyncMock()
            mock_enqueue.return_value = AsyncMock()
            mock_eta.return_value = 12
            mock_loc.return_value = (53.3501, -6.2661, datetime.now(timezone.utc)) # Near Dublin center

            secret = os.getenv("WHATSAPP_APP_SECRET", "dummy_secret")

            # Scenario A: Technician sends "I'm on my way"
            from src.uimodels import SendStatusTool
            mock_parser.return_value = SendStatusTool(query="Alice", status_type="on_way")
            
            tech_phone = "+444555666"
            payload = {"from_number": tech_phone, "body": "I am on my way to Alice"}
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
            
            response = await ac.post(
                "/webhook",
                content=payload_bytes,
                headers={"X-Hub-Signature-256": f"sha256={signature}", "Content-Type": "application/json"}
            )
            assert response.status_code == 200
            
            # Confirm by Tech
            mock_parser.return_value = None # Clear for "Yes"
            payload_yes = {"from_number": tech_phone, "body": "Yes"}
            payload_yes_bytes = json.dumps(payload_yes).encode("utf-8")
            sig_yes = hmac.new(secret.encode("utf-8"), payload_yes_bytes, hashlib.sha256).hexdigest()
            response = await ac.post("/webhook", content=payload_yes_bytes, headers={"X-Hub-Signature-256": f"sha256={sig_yes}", "Content-Type": "application/json"})
            print(f"DEBUG: Confirm Response: {response.json()}")
            assert "✔ Sent status update" in response.json()["reply"]

            # Verify customer received message
            mock_enqueue.assert_called()
            cust_call_found = False
            for call in mock_enqueue.call_args_list:
                if call.kwargs.get("recipient_phone") == "+777888999":
                    assert "on our way" in call.kwargs.get("content").lower()
                    cust_call_found = True
            assert cust_call_found

            # Scenario B: Customer asks "Where is the tech?"
            from src.uimodels import CheckETATool
            mock_parser.return_value = CheckETATool()
            
            customer_phone = "+777888999"
            payload_cust = {"from_number": customer_phone, "body": "Where are you?"}
            payload_cust_bytes = json.dumps(payload_cust).encode("utf-8")
            sig_cust = hmac.new(secret.encode("utf-8"), payload_cust_bytes, hashlib.sha256).hexdigest()
            
            response = await ac.post(
                "/webhook",
                content=payload_cust_bytes,
                headers={"X-Hub-Signature-256": f"sha256={sig_cust}", "Content-Type": "application/json"}
            )
            assert "Please confirm" in response.json()["reply"]

            # Customer confirms
            mock_parser.return_value = None
            payload_cust_yes = {"from_number": customer_phone, "body": "Yes"}
            payload_cust_yes_bytes = json.dumps(payload_cust_yes).encode("utf-8")
            sig_cust_yes = hmac.new(secret.encode("utf-8"), payload_cust_yes_bytes, hashlib.sha256).hexdigest()
            response = await ac.post("/webhook", content=payload_cust_yes_bytes, headers={"X-Hub-Signature-256": f"sha256={sig_cust_yes}", "Content-Type": "application/json"})
            
            assert response.status_code == 200
            data = response.json()
            assert "12 minutes" in data["reply"]
            assert "Tech Tom" in data["reply"]

            # Scenario C: Customer asks for Invoice
            from src.tools.invoice_tools import SendInvoiceTool
            mock_parser.return_value = SendInvoiceTool(query="me")
            
            payload_inv = {"from_number": customer_phone, "body": "Send me my invoice"}
            payload_inv_bytes = json.dumps(payload_inv).encode("utf-8")
            sig_inv = hmac.new(secret.encode("utf-8"), payload_inv_bytes, hashlib.sha256).hexdigest()
            
            response = await ac.post(
                "/webhook",
                content=payload_inv_bytes,
                headers={"X-Hub-Signature-256": f"sha256={sig_inv}", "Content-Type": "application/json"}
            )
            assert "Please confirm" in response.json()["reply"]

            # Customer confirms
            mock_parser.return_value = None
            with patch("src.services.invoice_service.InvoiceService.create_invoice") as mock_create_inv:
                mock_invoice = AsyncMock()
                mock_invoice.public_url = "https://herecrm.app/i/abc"
                mock_invoice.payment_link = "https://stripe.com/pay/123"
                mock_invoice.id = 1
                mock_create_inv.return_value = mock_invoice
                
                response = await ac.post("/webhook", content=payload_cust_yes_bytes, headers={"X-Hub-Signature-256": f"sha256={sig_cust_yes}", "Content-Type": "application/json"})

                assert response.status_code == 200
                data = response.json()
                assert "https://herecrm.app/i/abc" in data["reply"]
                assert "https://stripe.com/pay/123" in data["reply"]

            # Scenario D: Customer confirms a Quote
            async with SessionLocal() as db:
                from src.models import Quote
                quote = Quote(
                    business_id=biz.id,
                    customer_id=customer.id,
                    job_id=job.id,
                    total_amount=150.0,
                    status="sent",
                    external_token="test_token_123"
                )
                db.add(quote)
                await db.commit()
            
            response = await ac.post("/quotes/test_token_123/confirm")
            assert response.status_code == 200
            assert response.json()["status"] == "success"
            
            async with SessionLocal() as db:
                from sqlalchemy import select
                from src.models import Quote
                res = await db.execute(select(Quote).where(Quote.external_token == "test_token_123"))
                updated_quote = res.scalar_one()
                assert updated_quote.status == "accepted"

    if os.path.exists("test_customer_pov.db"):
        os.remove("test_customer_pov.db")
    print("\nAll Customer POV Tests Passed!")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_customer_pov_scenarios())
