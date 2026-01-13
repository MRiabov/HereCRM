---
work_package_id: WP04
subtasks:
  - T014
  - T015
  - T016
  - T017
lane: planned
history:
  - date: 2026-01-13
    status: planned
    agent: spec-kitty
---
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
