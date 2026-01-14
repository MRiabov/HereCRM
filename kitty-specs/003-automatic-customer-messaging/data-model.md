# Data Model: 003 Automatic Customer Messaging

## Entities

### `MessageLog`

Tracks the history of automated messages sent to customers.

- **Table**: `message_logs`
- **Fields**:
  - `id`: Integer (PK)
  - `recipient_phone`: String (E.164 format)
  - `content`: String (Text)
  - `message_type`: Enum (`WHATSAPP`, `SMS`) - default `WHATSAPP`
  - `status`: Enum (`PENDING`, `SENT`, `FAILED`)
  - `trigger_source`: String (e.g., "job_booked", "on_my_way")
  - `external_id`: String (Nullable, Meta Message ID)
  - `created_at`: DateTime (UTC)
  - `sent_at`: DateTime (Nullable, UTC)
  - `error_message`: String (Nullable)

## Events (Internal Event Bus)

### `JobBookedEvent`

Triggered when a job is created/booked.

- **Payload**:
  - `job_id`: Integer
  - `customer_id`: Integer
  - `customer_name`: String
  - `customer_phone`: String
  - `job_description`: String

### `JobScheduledEvent`

Triggered when a job is scheduled.

- **Payload**:
  - `job_id`: Integer
  - `schedule_time`: DateTime
  - `customer_phone`: String

### `OnMyWayEvent`

Triggered by pro user.

- **Payload**:
  - `customer_id`: Integer
  - `customer_phone`: String
  - `eta_minutes`: Integer (Optional)

## API Contracts (Internal)

### `MessagingService` Interface

- `send_message(recipient: str, content: str, channel: str = "whatsapp") -> MessageLog`
- `process_queue()`: Background task to consume from `asyncio.Queue`
