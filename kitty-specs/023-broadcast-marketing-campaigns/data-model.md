# Data Model: Broadcast Marketing Campaigns

## Entities

### Campaign

Represents a bulk messaging event.

| Field | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Unique identifier |
| `name` | String | Internal name for the campaign |
| `query_string` | String | The natural language query used to segment audience |
| `channel` | Enum | `email`, `whatsapp`, `sms` |
| `message_template` | Text | The content of the message |
| `status` | Enum | `draft`, `scheduled`, `running`, `paused`, `completed` |
| `total_recipients` | Integer | Count of targets |
| `sent_count` | Integer | Successfully sent messages |
| `failed_count` | Integer | Failed messages |
| `created_at` | DateTime | Creation timestamp |
| `scheduled_at` | DateTime (Nullable) | When to start sending |
| `completed_at` | DateTime (Nullable) | When finished |

### CampaignRecipient

Links a campaign to a specific customer and tracks individual delivery status.

| Field | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Unique identifier |
| `campaign_id` | Integer (FK) | Link to Campaign |
| `customer_id` | Integer (FK) | Link to Customer |
| `status` | Enum | `pending`, `sent`, `failed` |
| `error_message` | String (Nullable) | Error details if failed |
| `sent_at` | DateTime (Nullable) | Timestamp of sending |

## Enums

### ChannelType

- `EMAIL`
- `WHATSAPP`
- `SMS`

### CampaignStatus

- `DRAFT`: Initial creation, not yet launched.
- `SCHEDULED`: Confirmed and waiting for start time.
- `RUNNING`: Currently processing batches.
- `PAUSED`: Manually stopped or halted by error.
- `COMPLETED`: All recipients processed.

### RecipientStatus

- `PENDING`: Waiting to be picked up.
- `SENT`: Message successfully handed off to provider.
- `FAILED`: Provider returned error or internal error.
