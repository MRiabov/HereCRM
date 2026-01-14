# Quickstart: 003 Automatic Customer Messaging

## Environment Variables

Add these to `.env`:

```bash
META_API_TOKEN="your_access_token"
META_PHONE_NUMBER_ID="your_phone_id"
WHATSAPP_VERIFY_TOKEN="your_verify_token" # For webhook verification
```

## Running the Messaging Service

The messaging service runs as part of the main application process (since it uses an internal `asyncio.Queue` and Event Bus).
Just run the app normally:

```bash
uv run fastapi dev src/main.py
```

## Triggering Events (Dev Mode)

You can trigger test events via the CLI (to be implemented):

```bash
# Example
uv run python -m src.cli trigger --event on-my-way --customer 123
```

Or via the Python shell:

```python
from src.services.event_bus import event_bus
from src.services.events import OnMyWayEvent

await event_bus.publish(OnMyWayEvent(customer_id=123, customer_phone="+1234567890"))
```
