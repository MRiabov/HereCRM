# Quickstart: Multi-channel Communication

## Prerequisites

- Twilio Account SID & Auth Token (for SMS)
- Postmark Server Token (for Email)
- Python 3.12+ environment

## Configuration

Set the following environment variables:

```bash
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=...

POSTMARK_SERVER_TOKEN=...
POSTMARK_FROM_EMAIL=...
```

## Running the Webhook

The generic webhook is available at:
`POST /api/webhooks/generic`

Example Payload:

```json
{
  "identity": "+1234567890",
  "content": "Hello from external system",
  "metadata": { "source": "Zapier" }
}
```

## Testing Auto-Confirmation

1. Send an SMS: "Create a job for cleaning tomorrow".
2. System replies: "I've drafted a cleaning job... Auto-executing in 45s unless you reply 'cancel'".
3. Wait 45s.
4. Verify job created in DB.
