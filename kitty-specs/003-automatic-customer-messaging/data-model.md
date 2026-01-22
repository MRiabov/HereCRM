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

### `FollowUpDraft` (Proposed)

Stores AI-generated follow-up messages awaiting approval.

- **Table**: `followup_drafts`
- **Fields**:
  - `id`: Integer (PK)
  - `quote_id`: Integer (FK to quotes)
  - `customer_id`: Integer (FK)
  - `content`: String (The AI-generated draft)
  - `status`: Enum (`PENDING`, `APPROVED`, `REJECTED`, `SENT`)
  - `created_at`: DateTime (UTC)

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

### `QUOTE_SENT`

Triggered when a quote is successfully sent to a customer.

- **Payload**:
  - `quote_id`: Integer
  - `customer_id`: Integer

### `JOB_PAID`

Triggered when a job is marked as paid (Spec 018).

- **Payload**:
  - `job_id`: Integer
  - `customer_id`: Integer

## API Contracts (Internal)

### `MessagingService` Interface

- `send_message(recipient: str, content: str, channel: str = "whatsapp") -> MessageLog`
- `schedule_delayed_message(recipient: str, content: str, delay_hours: int, trigger_source: str)`
- `process_queue()`: Background task to consume from `asyncio.Queue`
