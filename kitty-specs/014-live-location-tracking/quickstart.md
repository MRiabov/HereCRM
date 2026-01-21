# Quickstart: Live Location Tracking

## Prerequisites

1. **Environment Variables**:
   - `OPENROUTE_API_KEY`: Must be set for ETA calculations.
   - `WHATSAPP_VERIFY_TOKEN`: For webhook verification if using live setup.

2. **Data Setup**:
   - Create a `User` (Employee) with a known phone number.
   - Create a `Customer` and a `Job` assigned to that employee scheduled for today.

## Testing Steps

### 1. Update Employee Location (Simulated)

You can simulate a WhatsApp location update by injecting a message payload or updating the DB directly.

**Option A: Direct DB Update (Python Reconstruct)**

```python
from src.database import SessionLocal
from src.models import User
from src.services.location_service import LocationService

async def set_location():
    async with SessionLocal() as db:
        repo = LocationService(db)
        # Assuming User ID 1 is your employee
        await repo.update_user_location(user_id=1, lat=53.3498, lng=-6.2603) # Dublin Spire
```

**Option B: WhatsApp Webhook Simulation (Direct API)**
Send a POST to `/webhooks/whatsapp` (if running locally with ngrok).
*Payload structure approximates the Cloud API format:*

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "123456789",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "15555555555",
              "phone_number_id": "123456123"
            },
            "contacts": [{ "profile": { "name": "Employee Name" }, "wa_id": "15551234567" }],
            "messages": [
              {
                "from": "15551234567",
                "id": "wamid.HBgLMDA...",
                "timestamp": "1660000000",
                "type": "location",
                "location": {
                  "latitude": 53.3498,
                  "longitude": -6.2603,
                  "name": "The Spire",
                  "address": "O'Connell Street Upper, Dublin 1"
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

### 2. Check ETA (Customer Flow)

1. Ensure the Customer (e.g. `whatsapp:+9876543210`) has an ACTIVE job with Employee (ID 1).
2. As the Customer, send: *"When will the technician arrive?"*
3. Verify the response is approximately: *"We are approximately X minutes away."*

### 3. Admin Locate (Business Owner Flow)

1. As the Business Owner, send: *"Locate EmployeeName"*
2. Verify response contains a Google Maps link.

## Troubleshooting

- **"Technician location unknown"**: Ensure `location_updated_at` is recent (< 30 mins).
- **"No active job found"**: Ensure the Job status is `scheduled` or `in_progress` and the time window covers NOW.
