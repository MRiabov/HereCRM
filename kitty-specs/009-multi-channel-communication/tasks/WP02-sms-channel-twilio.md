---
work_package_id: WP02
subtasks:
  - T007
  - T008
  - T009
  - T010
lane: "doing"
agent: "codex"
history:
  - date: 2026-01-19
    action: created
---

# WP02 - SMS Channel Support (Twilio)

## Objective

Implement SMS sending and receiving capabilities using Twilio, mapped to the core unified User model.

## Context

We need to support SMS as a fallback or primary channel. Twilio is the chosen provider.

## Subtasks

### T007: Implement TwilioService

- Create `src/services/twilio_service.py`.
- Methods: `send_sms(to_number: str, body: str)`.
- Use `twilio` python library (add to requirements.txt if missing).
- Env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.

### T008: Implement Inbound Webhook

- Create endpoint: `POST /webhooks/twilio`.
- Validate Twilio signature (security).
- Parse `From` and `Body` from payload.

### T009: Link Inbound SMS to User

- Logic: Find `User` where `phone_number` matches `From`.
- If found, create `Message` linked to `user_id`.
- If not found, create new `User` (auto-create? or reject? Spec implies "New user" is acceptable, or handled by next steps. Assume create logic is centralized).
- *Decision*: Map to `DataManagementService` or similar to handle user lookup/creation.

### T010: Update Message Routing

- Update the main message handler (likely `ConversationManager` or similar) to check user's active channel.
- If response is needed, delegate to `TwilioService.send_sms` if channel is SMS.

## Test Strategy

- **Unit**: Mock Twilio client to test `send_sms` logic.
- **Integration**: Use `ngrok` or similar to test local webhook handling with real Twilio (if dev env allows) or simulate POST requests with valid signatures.

## Activity Log

- 2026-01-19T17:53:23Z – codex – lane=doing – Started implementation
