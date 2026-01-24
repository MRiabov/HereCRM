---
work_package_id: WP03
title: Webhook Synchronization
lane: planned
dependencies: []
subtasks: [T007, T008]
---

## Objective

Implement a secure webhook endpoint to receive real-time data updates from Clerk.

## Context

Clerk sends events (`user.created`, `organization.updated`, etc.) to keep external databases in sync. We need to handle these to maintain our `users` and `businesses` tables.

## Subtasks

### T007: Webhook Endpoint Setup

**Purpose**: Receive POST requests from Clerk.
**Steps**:

1. Create `src/api/webhooks/clerk.py`.
2. Define `POST /webhooks/clerk`.
3. Implement Svix verification:
   - Request headers: `svix-id`, `svix-timestamp`, `svix-signature`.
   - Secret: `CLERK_WEBHOOK_SECRET` (from env).
   - Use `svix` library (install if needed, or implement raw HMAC SHA256 check if simple). *Recommendation: Install `svix`*.
   - Return 400 if signature invalid.

### T008: Event Handlers

**Purpose**: Process business logic based on event type.
**Steps**:

1. Inside the endpoint, parse `event.type`.
2. **`user.created` / `user.updated`**:
   - Extract `id` (clerk_id), `email_addresses`, `phone_numbers`.
   - Update/Create `User` by `clerk_id` OR `email` (to link legacy users).
3. **`organization.created` / `organization.updated`**:
   - Extract `id` (clerk_org_id), `name`.
   - Update/Create `Business`.
4. **`organizationMembership.created`**:
   - Link the relevant `User` to `Business`.
5. Return 200 OK to acknowledge receipt.

## Risks

- **Data consistency**: Ensure updates don't overwrite newer data if events arrive out of order (though Svix timestamp helps, we mostly trust the latest webhook).
- **Missing dependencies**: Add `svix` to pyproject.toml if using the library.
