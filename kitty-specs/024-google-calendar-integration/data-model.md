# Data Model: Google Calendar Integration

## Entities

### User (Modifications)

| Field | Type | Description |
|-------|------|-------------|
| `google_calendar_credentials` | `JSON` (or `Text`) | Stores the OAuth2 credentials blob (refresh_token, etc.). |
| `google_calendar_sync_enabled` | `Boolean` | Master switch for sync. Default `False`. |

### Job (Modifications)

| Field | Type | Description |
|-------|------|-------------|
| `gcal_event_id` | `String` | The Google Calendar Event ID associated with this job. Used for updates/deletes. Nullable. |

## Relationships

No new relationships.

## Validation / Constraints

- `gcal_event_id` keys unique? Effectively yes, but not strictly enforced by DB constraint usually (uniqueness on GCal side).
- `google_calendar_credentials` should be protected/excluded from standard API serializations.
