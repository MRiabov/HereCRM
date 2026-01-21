# Data Model

## New Entity: `CustomerAvailability`

Represents a time window when a customer is available for service.

| Field | Type | Constraint | Description |
|---|---|---|---|
| `id` | Integer | PK, Auto-inc | Unique identifier |
| `business_id` | Integer | FK `businesses.id` | Multi-tenant isolation |
| `customer_id` | Integer | FK `customers.id` | The customer |
| `start_time` | DateTime | Not Null, UTC | Window start |
| `end_time` | DateTime | Not Null, UTC | Window end |
| `created_at` | DateTime | Default Now | Audit |

**Relationships:**

- `Customer` (1) -> (N) `CustomerAvailability`

## Entity Updates

### `User` (Employees)

| Field | Type | Default | Description |
|---|---|---|---|
| `default_start_lat` | Float | Nullable | Start location Latitude |
| `default_start_lng` | Float | Nullable | Start location Longitude |

### `Job`

| Field | Type | Default | Description |
|---|---|---|---|
| `estimated_duration` | Integer | `60` | Duration in minutes. Overrides Service duration if set. |

### `Service`

| Field | Type | Default | Description |
|---|---|---|---|
| `estimated_duration` | Integer | `60` | Default duration in minutes for jobs of this service type. |

## Database Indexes

- `CustomerAvailability(customer_id, start_time)`: For fast lookup during routing.
- `Job(scheduled_at)`: Existing, relevant for conflict checks.
