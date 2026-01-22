# Data Model: Job Documents

## Entities

### Document

Represents a file or link associated with a customer or specific job.

| Field | Type | Attributes | Description |
|-------|------|------------|-------------|
| `id` | Integer | PK | Unique identifier |
| `business_id` | Integer | FK | Reference to `Business` |
| `customer_id` | Integer | FK | Reference to `User` (Customer) |
| `job_id` | Integer | FK, Nullable | Reference to `Job`. Null if general customer doc. |
| `doc_type` | String | | Enum: `internal_upload`, `external_link` |
| `storage_path` | String | | S3 Key (for internal) or Full URL (for external) |
| `filename` | String | | Original filename or link title |
| `mime_type` | String | | e.g., `image/jpeg`, `application/pdf` |
| `size_bytes` | Integer | | File size in bytes |
| `created_at` | DateTime | | Upload timestamp |

## Relationships

* **User (Customer)** has many **Documents**.
* **Job** has many **Documents**.
* **Business** has many **Documents**.
