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

## Events (Shared Event Bus)

The messaging system listens for strings emitted via `src.events.event_bus`.

### `JOB_CREATED`

Common event from `CRMService.create_job`.

- **Payload**:
  - `job_id`: Integer
  - `customer_id`: Integer
  - `business_id`: Integer

### `JOB_SCHEDULED`

New event to be emitted when a job's `scheduled_at` is set or changed.

- **Payload**:
  - `job_id`: Integer
  - `scheduled_at`: ISO String
  - `customer_id`: Integer
  - `business_id`: Integer

### `ON_MY_WAY` (Proposed)

Ad-hoc event triggered by user.

- **Payload**:
  - `customer_id`: Integer
  - `eta_minutes`: Integer (Optional)
  - `business_id`: Integer

## API Contracts (Internal)

### `MessagingService` Interface

- `send_message(recipient: str, content: str, channel: str = "whatsapp") -> MessageLog`
- `process_queue()`: Background task to consume from `asyncio.Queue`
