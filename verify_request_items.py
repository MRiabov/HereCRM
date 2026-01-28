import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from src.database import async_session_factory
from src.services.crm_service import CRMService
from src.models import Urgency, RequestStatus

async def verify_request_creation():
    async with async_session_factory() as session:
        service = CRMService(session, business_id=1, user_id=1)
        
        print("Creating request with line items...")
        try:
            items = [
                {"description": "Test Item 1", "quantity": 2, "unit_price": 50.0},
                {"description": "Test Item 2", "quantity": 1, "unit_price": 100.0}
            ]
            
            request = await service.create_request(
                description="Verification Request",
                customer_id=1, # Assuming customer 1 exists, if not code might fail but we'll see
                urgency=Urgency.HIGH,
                items=items,
                customer_details={"name": "Test User", "phone": "1234567890"}
            )
            
            print(f"Request created: ID {request.id}")
            print(f"Urgency: {request.urgency}")
            print(f"Status: {request.status}")
            print(f"Expected Value: {request.expected_value}")
            
            # Refresh to load line items if not loaded
            # (service returns it with refresh, but let's be sure)
            print(f"Line Items ({len(request.line_items)}):")
            for item in request.line_items:
                print(f" - {item.description}: {item.quantity} x {item.unit_price} = {item.total_price}")

            assert len(request.line_items) == 2
            assert request.urgency == Urgency.HIGH
            assert request.expected_value == 200.0 # (2*50 + 1*100)
            
            print("\nVerification SUCCESS!")
            
        except Exception as e:
            print(f"\nVerification FAILED: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_request_creation())
