# Data Model for Feature 006

## New Entities

### Invoice

Represents a generated invoice for a specific job.

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | Integer (PK) | Yes | Unique identifier |
| `job_id` | Integer (FK) | Yes | Link to the Job being invoiced |
| `created_at` | DateTime | Yes | When the invoice was generated |
| `s3_key` | String | Yes | Path/Key in the S3 bucket |
| `public_url` | String | Yes | Publicly accessible URL (or presigned) |
| `status` | Enum | Yes | `DRAFT`, `SENT`, `PAID`, `CANCELLED` |

## Modified Entities

### Job

- `invoices`: One-to-Many relationship to `Invoice` (usually one-to-one in practice, but allows re-issuing).
