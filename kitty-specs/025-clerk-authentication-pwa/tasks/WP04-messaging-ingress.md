---
work_package_id: WP04
title: Messaging Ingress & Registration
lane: "doing"
dependencies: []
subtasks: [T009, T010]
agent: "Antigravity"
shell_pid: "587193"
---

## Objective

Update the messaging ingress flow to prevent auto-creation of users and instead guide them to register via Clerk.

## Context

Currently, `auth_service.get_or_create_user` might auto-create a user when a message arrives from a new number (or it might fail). We want to strictly enforce that ONLY registered users can interact. Unknown numbers should receive a "Welcome" message with a signup link.

## Subtasks

### T009: Refactor Auth Service

**Purpose**: Change user resolution logic.
**Steps**:

1. Open `src/services/auth_service.py`.
2. Rename/Modify `get_or_create_user` to `resolve_user_from_ingress(phone_number)`.
3. Logic:
   - Query DB for `User` with this phone number.
   - If found: Return `User`.
   - If NOT found: Return `None`. (Remove any "create" logic).

### T010: Handle Unknown Senders

**Purpose**: Reply with invitation.
**Steps**:

1. Open `src/api/routes.py` (specifically the WhatsApp/Twilio webhook handler).
2. Call `resolve_user_from_ingress`.
3. If `user is None`:
   - Construct a friendly message: "Welcome to HereCRM! Please sign in to verify your identity: {CLERK_SIGNUP_URL}".
   - Send this reply via the messaging service.
   - **STOP** processing. Do not pass this message to the command processor or store it as an interaction.

## Risks

- **Lost leads**: We are effectively ignoring messages from non-users. Ensure the signup flow is robust.
- **Config**: Need `CLERK_SIGNUP_URL` in config/env.

## Activity Log

- 2026-01-25T08:14:13Z – Antigravity – shell_pid=587193 – lane=doing – Started review via workflow command
