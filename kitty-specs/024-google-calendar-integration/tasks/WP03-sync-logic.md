---
work_package_id: WP03
title: Calendar Sync Logic
lane: "doing"
dependencies: []
subtasks: [T010, T011, T012, T013]
agent: "Antigravity"
shell_pid: "328681"
---

# WP03 - Calendar Sync Logic (Service Layer)

## Objective

Implement CRUD operations against the Google Calendar API within `GoogleCalendarService`.

## Context

Now that we have credentials, we need to actually create/update/delete events. This WP focuses purely on the API interactions.

## Subtasks

### T010: Implement `create_event`

**Purpose**: Create an event on the user's primary calendar.
**Steps**:

1. Implement `create_event(self, job: Job, user_creds_json: str) -> str`:
   - Load credentials (use helper from T013).
   - Build service: `build('calendar', 'v3', credentials=creds)`.
   - Construct body:

     ```python
     event = {
       'summary': f"Job for {job.client_name}",
       'location': job.address,
       'description': job.description,
       'start': {'dateTime': job.scheduled_start.isoformat(), 'timeZone': 'UTC'}, # Verify TZ!
       'end': {'dateTime': job.scheduled_end.isoformat(), 'timeZone': 'UTC'},
     }
     ```

   - Call `service.events().insert(calendarId='primary', body=event).execute()`.
   - Return `event['id']`.

### T011: Implement `update_event`

**Purpose**: Update details of an existing event.
**Steps**:

1. Implement `update_event(self, job: Job, event_id: str, user_creds_json: str)`:
   - Same setup.
   - Call `service.events().update(calendarId='primary', eventId=event_id, body=event).execute()`.
   - Handle `404 Not Found` (e.g. user deleted it manually) -> Re-create it? Or log warning. *Decision*: Log warning and clear `gcal_event_id` in caller (or return status).

### T012: Implement `delete_event`

**Purpose**: Remove event (e.g. on unassignment).
**Steps**:

1. Implement `delete_event(self, event_id: str, user_creds_json: str)`:
   - Call `service.events().delete(calendarId='primary', eventId=event_id).execute()`.
   - Handle `404` gracefully (already gone).

### T013: Credential Loading & Refresh

**Purpose**: Ensure implementation handles expired tokens.
**Steps**:

1. Helper method `_get_credentials(json_blob)`:
   - `creds = google.oauth2.credentials.Credentials.from_authorized_user_info(info)`
   - `if creds.expired and creds.refresh_token: creds.refresh(Request())` -> This requires `google_auth.transport.requests.Request`.
   - Return valid creds.
   - *Note*: If refresh happens, we technically should update the DB with the new access token, though it's optional if `google-auth` handles it in-memory. Better to update DB if `creds.to_json()` changes.

## Validation

- [ ] Unit tests mocking `build` and `service.events().insert/...`.
- [ ] Verify `_get_credentials` refreshes token if expired (mock `creds.expired = True`).

## Risks

- **Timezones**: Critical. Ensure `job.scheduled_start` is timezone-aware or we know it's UTC. If native, `isoformat()` might look like `2023-01-01T10:00:00` (no Z). Google interprets this as "local time of the calendar".
  - *Mitigation*: Ensure we send correct timezone info. If CRM is UTC, suffix with 'Z'.
- **Rate Limits**: `execute()` hooks are blocking.

## Activity Log

- 2026-01-24T11:03:45Z – Antigravity – shell_pid=318543 – lane=doing – Started implementation via workflow command
- 2026-01-24T11:08:37Z – Antigravity – shell_pid=318543 – lane=for_review – Ready for review: Implemented Google Calendar CRUD operations and credential management with unit tests. Merged WP02 changes for foundation.
- 2026-01-24T11:11:11Z – Antigravity – shell_pid=328681 – lane=doing – Started review via workflow command
