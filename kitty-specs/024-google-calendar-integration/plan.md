# Implementation Plan: Google Calendar Integration

*Path: kitty-specs/024-google-calendar-integration/plan.md*

**Branch**: `024-google-calendar-integration` | **Date**: 2026-01-24 | **Spec**: [Spec 024](spec.md)
**Input**: Feature specification from `kitty-specs/024-google-calendar-integration/spec.md`

## Summary

Implement a one-way synchronization of jobs from HereCRM to a user's personal Google Calendar. This feature enables field workers to view their schedule in their native calendar apps. We will use the Google Calendar API via `google-api-python-client` and standard OAuth2 web flow (`/auth/google/callback`). Synchronization will be event-driven using the `EventBus` to listen for job scheduling changes.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**:

- `google-api-python-client` (Google APIs)
- `google-auth-oauthlib` (OAuth2 flow)
- `google-auth` (Auth helpers)
- Existing: FastAPI, SQLAlchemy, Pydantic, EventBus
**Storage**: SQLite (with SQLCipher) - Update `User` table to store OAuth credentials.
**Testing**: pytest with `unittest.mock` for Google APIs.
**Target Platform**: Linux server (Project runs on Linux).
**Project Type**: Single project (Monolith structure in `src/`).
**Performance Goals**: Sync changes within 10s of event. Background processing logic to avoid blocking user request.
**Constraints**:
- Must handle token expiration/refresh automatically.
- Must respect Google API rate limits.
- Strict one-way sync (CRM -> GCal).
**Scale/Scope**: Per-user integration. Expecting low volume of sync events per user per day (<50).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Directive | Check | Notes |
|:---|:---|:---|
| **1. LLM-First Text Processing** | N/A | Feature is primarily deterministic (API integration). LLM parsing of "Schedule job" commands is covered in other specs. |
| **2. Intent Transparency and Control** | PASS | User manually authorizes access. "Disconnect" option provided. Sync is implicit but user is notified on connection. |
| **3. Progressive Documentation & Assistant** | PENDING | Must update `manual.md` and help messages (Spec requirement 2.3). |

## Project Structure

### Documentation (this feature)

```
kitty-specs/024-google-calendar-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```
src/
├── api/
│   └── routes.py                # Add /auth/google/login and /auth/google/callback
├── models/
│   └── user.py                  # Update User model with calendar credentials
├── services/
│   ├── google_calendar_service.py # New service for API interactions
│   └── messaging_service.py     # Listen to JOB events and trigger sync
├── lib/
│   └── google_auth.py           # (Optional) Helper for auth flow if service gets too large
tests/
├── integration/
│   └── test_google_calendar_sync.py
└── unit/
    └── test_google_calendar_service.py
```

**Structure Decision**: Standard Service-based architecture. A new `GoogleCalendarService` will handle both the OAuth flow logic and the Calendar API operations. It will subscribe to `EventBus` events to trigger syncs.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New Dependencies | Google API interaction | writing raw HTTP requests is error-prone and harder to maintain auth logic. |
