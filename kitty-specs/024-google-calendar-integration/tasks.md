# Tasks: Spec 024 - Google Calendar Integration

**Spec**: [Spec 024](spec.md) | **Status**: Planned | **Context**: 024-google-calendar-integration

## Work Packages

### WP01 - Foundation & Data Models

**Goal**: Prepare environment, dependencies, and database schema for calendar integration.
**Priority**: Critical (Blocker)
**Test Strategy**: Verify migrations run successfully and schema reflects changes.

- [x] **T001**: Install Python dependencies (`google-api-python-client`, `google-auth-oauthlib`, `google-auth`).
- [x] **T002**: Add and validate environment variables (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`) in settings.
- [x] **T003**: Migration: Add `google_calendar_credentials` (JSON) and `google_calendar_sync_enabled` (bool) to `User` model.
- [x] **T004**: Migration: Add `gcal_event_id` (string) to `Job` model.

**Parallelism**: Blocked by none. Blocks WP02.
**Est. Prompt Size**: ~300 lines

---

### WP02 - OAuth Authentication Flow

**Goal**: Implement the OAuth2 flow to allow users to connect their Google Calendar.
**Priority**: High
**Test Strategy**: Manual verification of auth flow via browser; Unit tests for service methods.

- [ ] **T005**: data structure for `GoogleCalendarService` to handle auth logic.
- [ ] **T006**: Implement `get_auth_url()` using `Flow.from_client_config`.
- [ ] **T007**: Implement `process_auth_callback(code)` to exchange code for credentials and save to `User`.
- [ ] **T008**: Create API routes `GET /auth/google/login` and `GET /auth/google/callback` in `src/api/routes.py`.
- [ ] **T009**: Verify auth flow stores credentials correctly in DB.

**Parallelism**: Depends on WP01. Blocks WP03.
**Est. Prompt Size**: ~450 lines

---

### WP03 - Calendar Sync Logic (Service Layer)

**Goal**: Implement the core CRUD operations for Google Calendar within the service.
**Priority**: High
**Test Strategy**: Mock Google API responses to verify service logic.

- [ ] **T010**: Implement `create_event(job, user_creds)`: Maps job fields to GCal Event resource.
- [ ] **T011**: Implement `update_event(job, event_id, user_creds)`: Updates existing event.
- [ ] **T012**: Implement `delete_event(event_id, user_creds)`: Removes event.
- [ ] **T013**: Implement credential loading and automatic refresh logic using `google.oauth2.credentials`.

**Parallelism**: Depends on WP02. Blocks WP04.
**Est. Prompt Size**: ~400 lines

---

### WP04 - Event Bus Integration

**Goal**: Hook up the sync service to system events to trigger syncs automatically.
**Priority**: High
**Test Strategy**: Emit fake `JOB_CREATED`/`JOB_UPDATED` events and verify service methods are called.

- [ ] **T014**: Subscribe `GoogleCalendarService` to `JOB_CREATED`, `JOB_UPDATED`, `JOB_ASSIGNED` events.
- [ ] **T015**: Implement logic: On Job Creation/Assignment -> Create GCal Event.
- [ ] **T016**: Implement logic: On Job Update -> Update GCal Event.
- [ ] **T017**: Implement logic: On Reassignment -> Delete from Old User, Create for New User.

**Parallelism**: Depends on WP03. Blocks WP05.
**Est. Prompt Size**: ~350 lines

---

### WP05 - Polish & Documentation

**Goal**: Finalize UX responses and update documentation.
**Priority**: Medium
**Test Strategy**: Visual check of help docs and bot responses.

- [ ] **T018**: send confirmation message on successful auth ("✔ Google Calendar connected! ...").
- [ ] **T019**: Update `src/assets/manual.md` with "Google Calendar Integration" section.

**Parallelism**: Depends on WP04.
**Est. Prompt Size**: ~200 lines
