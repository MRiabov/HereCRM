---
work_package_id: WP04
subtasks:
  - T014
  - T015
  - T016
  - T017
lane: "planned"
review_status: "has_feedback"
reviewed_by: "Antigravity"
agent: spec-kitty
history:
  - date: 2026-01-13
    status: planned
    agent: spec-kitty
---
## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **Broken Tests Out-of-the-Box**: `tests/test_webhook_e2e.py` fails during collection if `GOOGLE_API_KEY` is not set in the environment. Pydantic validation error occurs at import time.
   - **Fix**: Mock `Settings` or `GOOGLE_API_KEY` in `conftest.py` or use a `.env.test` file. Tests must run `pytest` without extra setup.
2. **Security - Error Leakage**: `src/api/routes.py:45` `detail=f"Onboarding failed: {str(e)}"` leaks internal exception details to the caller.
   - **Fix**: Log the error and return a generic "Internal Server Error" or "Processing Failed" message.
3. **Security - Missing Signature**: No validation of WhatsApp webhook signature.
   - **Action**: Add a TODO or basic token check if full HMAC verification is out of scope for now.

**What Was Done Well**:

- Clean separation of concerns (Auth vs Service).
- Integration test covers the full flow clearly.

**Action Items**:

- [ ] Fix test suite to run without external env vars.
- [ ] Sanitize API error responses (no exception strings).
- [ ] Add TODO/Basic Auth for webhook security.

# Work Package: Onboarding & End-to-End Wiring

## Objective

Connect the internal logic to the outside world via a Webhook and implement the automated onboarding flow that creates new Businesses and Users on the fly.

## Context

Users interact via HTTP POST to our webhook. We need to identify them by phone number. If they are new, we auto-create a Business for them (making them the Owner). If they are an existing user, we look up their Business.

## Subtasks

### T014: Webhook Entrypoint

- Create `src/api/routes.py`.
- Define `POST /webhook`.
- Accept standard WhatsApp payload (or a simplified stub given we are mocking it mostly).
- Extract `from_number` and `body`.

### T015: User Identification & Onboarding

- Create `src/services/auth_service.py` (or part of `WhatsappService`).
- Logic:
  - `user = user_repo.get(phone)`
  - If `user` exists: Return `user`.
  - If `user` missing:
    - Create `Business(name="Business of [Phone]")`.
    - Create `User(phone=phone, role=OWNER, business=new_business)`.
    - Return new `user`.

### T016: Wiring Pipeline

- In `POST /webhook`:
  - Call `auth_service.get_or_create_user(phone)`.
  - Call `whatsapp_service.handle_message(user.business_id, user.phone, body)`.
  - Return the response text to the caller.

### T017: Integration Tests

- Create `tests/test_webhook_e2e.py`.
- Use `TestClient` from FastAPI.
- Scenario:
  - POST /webhook with `phone="123"`, text="Add job...".
  - Assert response is "Confirm?".
  - POST /webhook with `phone="123"`, text="Yes".
  - Assert response is "Saved".
  - Verify DB contains the new Business, User, and Job.

## Definition of Done

- [ ] New phone numbers automatically trigger account creation.
- [ ] Full loop from HTTP Request -> DB -> HTTP Response works.
- [ ] Integration tests prove the "Zero-Friction Onboarding" scenario.

## Activity Log

- 2026-01-13T12:37:48Z – Antigravity – lane=doing – Started implementation
- 2026-01-13T12:41:39Z – Antigravity – lane=for_review – Ready for review
- 2026-01-13T13:10:00Z – Antigravity – lane=planned – Code review complete: Needs changes (Tests, Security)
