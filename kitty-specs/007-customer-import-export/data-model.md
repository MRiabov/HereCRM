# Data Model: Customer Import/Export

## New Entities

### ImportJob

Tracks the status and result of bulk data usage.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer (PK) | Unique ID |
| `business_id` | Integer (FK) | Owner business |
| `status` | String | 'pending', 'processing', 'completed', 'failed' |
| `file_url` | String | Source file URL |
| `filename` | String | Original filename |
| `created_at` | DateTime | Timestamp |
| `completed_at` | DateTime | Completion timestamp |
| `record_count` | Integer | Number of records processed |
| `error_log` | JSON | List of validation errors or failure reason |

### ExportRequest

Tracks requests to download data.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer (PK) | Unique ID |
| `business_id` | Integer (FK) | Owner business |
| `status` | String | 'pending', 'processing', 'completed', 'failed' |
| `query` | Text | Original natural language query |
| `format` | String | 'csv', 'excel', 'json' |
| `s3_key` | String | Path to generated file in S3 |
| `public_url` | String | Downloadable URL |
| `created_at` | DateTime | Timestamp |

## Updates to Existing Models

### ConversationStatus (Enum)

- Add: `DATA_MANAGEMENT`
  - Usage: User enters this mode via "Manage Data" command.
  - Behavior: Disables standard CRM tools, enables Import/Export tools.

## Relationships

- `Business` -> `ImportJob` (1:N)
- `Business` -> `ExportRequest` (1:N)
