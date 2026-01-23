# Data Model: Job Documents

## Entities

### Document

Represents a file or link associated with a customer or specific job.

| Field | Type | Attributes | Description |
|-------|------|------------|-------------|
| `id` | Integer | PK | Unique identifier |
| `business_id` | Integer | FK | Reference to `Business` |
| `customer_id` | Integer | FK | Reference to `User` (Customer) |
| `job_id` | Integer | FK, Nullable | Reference to `Job`. |
| `doc_type` | String | | Enum: `internal_upload`, `external_link`, `generated_pdf` |
| `category` | String | | Enum: `general`, `invoice`, `quote` |
| `storage_path` | String | | S3 Key (internal) or URL (external) |
| `filename` | String | | Original filename |
| `mime_type` | String | | e.g., `image/jpeg`, `application/pdf` |
| `size_bytes` | Integer | | File size in bytes |
| `created_at` | DateTime | | Upload timestamp |

### Quote (Update)

| Field | Change | Description |
|-------|--------|-------------|
| `blob_url` | **Remove** | Replaced by foreign key |
| `document_id` | **Add** | FK to `Document` (nullable) |

### Invoice (Update)

| Field | Change | Description |
|-------|--------|-------------|
| `s3_key` | **Remove** | Replaced by foreign key |
| `public_url` | **Remove** | Replaced by foreign key |
| `document_id` | **Add** | FK to `Document` (nullable) |

## Relationships

* **Quote** has one **Document** (optional).
* **Invoice** has one **Document** (optional).
* **Job** has many **Documents** (covers both user uploads and system files).
