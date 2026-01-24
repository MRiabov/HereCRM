# Research & Findings: Google Calendar Integration

## 1. Google API Authentication

**Decision**: Use `Authorization Code Flow` for web server applications.
**Rationale**:

- Users are interacting with HereCRM often via browser or can easily switch to browser.
- Provides long-lived access via `refresh_token`.
- Standard, secure pattern supported by `google-auth-oauthlib`.

**Library Choice**: `google-api-python-client` and `google-auth-oauthlib`.

- Official Google libraries.
- Handles token refreshing automatically.

**Scopes Required**:

- `https://www.googleapis.com/auth/calendar.events`: Read/write access to Events. We do NOT need full calendar access (creating calendars, ACLs) unless we strictly need to create a dedicated calendar.
- *Refinement*: The spec says "user's personal Google Calendar", which implies their primary calendar (`primary` keyword in API). So `calendar.events` is sufficient.

## 2. Synchronization Architecture

**Decision**: Event-Driven Sync via `EventBus`.
**Rationale**:

- `EventBus` already exists in `src/events.py`.
- Decouples `CRMService` from `GoogleCalendarService`.
- Allows `MessagingService` and `GoogleCalendarService` to both react to scheduling without knowing about each other.

**Events to Listen**:

- `JOB_SCHEDULED`: Trigger create/update.
- `JOB_CANCELLED`: Trigger delete.
- `JOB_ASSIGNED`: Trigger add to new user, delete from old.

**Data Flow**:

1. Event `JOB_SCHEDULED` emitted with `job_id`.
2. `GoogleCalendarService` receives event.
3. Fetch `Job` with `User` relation.
4. Check if `User.google_calendar_credentials` exists.
5. If yes, construct `gcal_event` payload.
6. Call `events().insert()` or `events().update()`.
7. Save `gcal_event_id` back to `Job`.

## 3. Data Storage

**Decision**: Store OAuth2 credentials as a JSON blob in `User` table.
**Rationale**:

- Simple.
- We need to store: `token`, `refresh_token`, `token_uri`, `client_id`, `client_secret` (or rely on env for client vars), `scopes`.
- The `google.oauth2.credentials.Credentials` object can be serialized/deserialized easily to JSON.

## 4. Rate Limiting & Errors

**Strategy**:

- Use `exponential backoff` (built-in to Google client? Need to verify or implement).
- Capture `google.auth.exceptions.RefreshError`. If refresh fails, set `User.google_calendar_sync_enabled = False` and notify user (or log it).
