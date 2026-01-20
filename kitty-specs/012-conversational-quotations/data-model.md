# Data Model: Conversational Quotations (012)

## Entities

### Quote

Represents a price proposal sent to a customer.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key |
| `customer_id` | UUID | FK to Customer |
| `business_id` | UUID | FK to Business |
| `status` | Enum | `DRAFT`, `SENT`, `ACCEPTED`, `REJECTED`, `EXPIRED` |
| `total_amount` | Decimal | Total value of the quote |
| `external_token` | String | Secure token for external confirmation |
| `blob_url` | String | S3 URL to the generated PDF |
| `job_id` | UUID | FK to Job (null until accepted) |
| `created_at` | DateTime | Timestamp |
| `updated_at` | DateTime | Timestamp |

### QuoteLineItem

Snapshot of services/products at the time of quote generation.

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID | Primary Key |
| `quote_id` | UUID | FK to Quote |
| `service_id` | UUID | FK to ServiceCatalog (optional) |
| `description` | String | Description of service |
| `quantity` | Integer | Quantity |
| `unit_price` | Decimal | Price per unit |
| `total` | Decimal | quantity * unit_price |

## Relationships

- **Customer (1) : (N) Quote**
- **Quote (1) : (N) QuoteLineItem**
- **Quote (0..1) : (1) Job** (Job created from Quote)

## State Transitions

1. `DRAFT` (Initial)
2. `DRAFT` -> `SENT` (PDF generated and link sent via WhatsApp/SMS)
3. `SENT` -> `ACCEPTED` (Confirmed via text or website)
4. `SENT` -> `REJECTED` (Explicit rejection)
5. `SENT` -> `EXPIRED` (Timeout, e.g., 30 days)
