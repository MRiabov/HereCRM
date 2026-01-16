# Data Model: Line Items & Service Catalog

## Service

Represents a reusable catalog item.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | PK |
| business_id | Integer | FK to Business |
| name | String | e.g. "Window Clean" |
| description | Text | Optional default description |
| default_price | Float | Standard unit price |
| created_at | DateTime | |

## LineItem

Represents a specific charge on a job.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | PK |
| job_id | Integer | FK to Job |
| description | String | Snapshot of service name or custom text |
| quantity | Float | e.g. 10.0, 1.5 |
| unit_price | Float | Price per unit (snapshot) |
| total_price | Float | helper (persist or compute?) -> Persist for query speed |
| service_id | Integer | Optional FK to Service (nullable, for ad-hoc items) |

## Job (Updated)

| Field | Type | Description |
|-------|------|-------------|
| ... | ... | ... |
| **line_items** | List[LineItem] | One-to-Many relationship |
| **value** | Float | **Computed** sum of line items (or manual override legacy?) |

*Note: For backward compatibility, `Job.value` should probably become a computed property or be kept in sync with sum(line_items).*
