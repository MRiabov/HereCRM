# Data Model

## Entities

### User (Update)

Existing model `src.models.User`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_latitude` | Float | No | Last known latitude. |
| `current_longitude` | Float | No | Last known longitude. |
| `location_updated_at` | DateTime (UTC) | No | Timestamp of the last update. |

**Indexes**:

- Index on `(business_id, location_updated_at)` might be useful for "who is active" queries, but premature optimization.

## Data Lifecycle

1. **Ingest**:
   - `WhatsAppService` -> `LocationService.update_location`.
   - Overwrites previous values.
   - Updates `location_updated_at` to `datetime.now(timezone.utc)`.

2. **Consumption**:
   - `LocationService.get_employee_location(user_id)` -> returns `(lat, lng, age)`.
   - **Stale Data Rule**: If `age > 30 mins`, consider location "Unknown" or "Stale" (warn user).

3. **Cleanup**:
   - No retention policy defined. We only store the *latest* point. We do not track history/breadcrumbs (privacy friendly).
