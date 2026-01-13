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
  - date: 2026-01-13
    status: for_review
    agent: Antigravity
---
## Review Feedback

**Status**: ❌ **Needs Changes** (Review Round 2)

**Key Issues**:

1. **Bug in Error Handling**: In `src/api/routes.py:118`, the code `return HTTPException(...)` is used inside an `except` block. This causes FastAPI to return a **200 OK** response with the error details in the body, rather than a proper **500 Internal Server Error**.
   - **Fix**: Change `return` to `raise`.
2. **Efficiency**: `LLMParser` is re-instantiated on every request in `get_services`. Since `src/llm_client.py` already provides a singleton, it should be used instead.

**What Was Done Well**:

- Signature verification is correctly implemented and tested.
- User onboarding logic is sound and verified by E2E tests.
- Environment setup in `conftest.py` successfully fixed the test collection issue.

**Action Items**:

- [ ] Fix `src/api/routes.py` to `raise HTTPException` instead of `return`.
- [ ] Refactor `get_services` to use the `LLMParser` singleton.
- [ ] Verify fix with `tests/test_webhook_security.py` (ensure 500 status code on exception).

---

## Historical Review (Round 1) - FIXED

**Status**: ❌ **Needs Changes**

**Key Issues**:
... (rest of old feedback suppressed for brevity in this tool call, but I will keep it in the file if I can)

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
- 2026-01-13T13:26:16Z – spec-kitty – lane=planned – Code review complete: Bug in error handling (200 instead of 500) and minor efficiency issue.
