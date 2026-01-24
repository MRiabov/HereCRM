# Implementation Plan - Clerk Authentication for PWA

This plan outlines the integration of Clerk for authentication, organization management, and the messaging ingress flow for new users.

## User Review Required

> [!IMPORTANT]
> This plan requires adding `clerk-backend-api`, `pyjwt`, and `cryptography` to project dependencies.
> We will adhere to the "Webhook Sync" pattern for data consistency, with a "Just-In-Time" fallback for login if webhooks lag.

## Proposed Changes

### Dependencies

#### [MODIFY] [pyproject.toml](file:///home/maksym/Work/proj/HereCRM/pyproject.toml)

- Add `clerk-backend-api` (Official SDK for management).
- Add `pyjwt` and `cryptography` (For high-performance local token validation).

### Database Schema

#### [This is a Migration]

1. **User Model**: Add `clerk_id` (String, Unique, Nullable).
2. **Business Model**: Add `clerk_org_id` (String, Unique, Nullable).
3. **Migration Script**: Generate alembic migration.

### Auth Infrastructure

#### [NEW] [src/api/dependencies/clerk_auth.py](file:///home/maksym/Work/proj/HereCRM/src/api/dependencies/clerk_auth.py)

- Implement `VerifyToken` dependency class.
- **Logic**:
    1. Extract Bearer token.
    2. Verify signature using Clerk JWKS (cached).
    3. Extract `sub` (User ID) and `org_id` (Organization ID).
    4. Lookup `User` by `clerk_id`.
    5. **JIT Fallback**: If `User` not found but token is valid, fetch details from Clerk SDK and create/sync `User` + `Business` immediately to avoid race conditions.
    6. Verify `User.business.clerk_org_id` matches the token's `org_id`.
    7. Return `User` instance.

#### [MODIFY] [src/config.py](file:///home/maksym/Work/proj/HereCRM/src/config.py)

- Add Clerk settings: `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_ISSUER`, `CLERK_JWKS_URL`.

### Webhook Synchronization

#### [NEW] [src/api/webhooks/clerk.py](file:///home/maksym/Work/proj/HereCRM/src/api/webhooks/clerk.py)

- Implement endpoint `POST /webhooks/clerk` with Svix signature verification (Clerk standard).
- **Handlers**:
  - `user.created` / `user.updated`: Sync `User` table.
  - `organization.created` / `organization.updated`: Sync `Business` table.
  - `organizationMembership.created`: Link `User` to `Business`.

### Messaging Ingress & Registration Flow

#### [MODIFY] [src/services/auth_service.py](file:///home/maksym/Work/proj/HereCRM/src/services/auth_service.py)

- Rename `get_or_create_user` to `resolve_user_from_ingress`.
- **Change Logic**:
  - Check if phone exists.
  - If **exists**: Return `User`.
  - If **not exists**: Return `None` (STOP auto-creation).

#### [MODIFY] [src/api/routes.py](file:///home/maksym/Work/proj/HereCRM/src/api/routes.py)

- Update `webhook` (WhatsApp/Twilio) logic:
  - Call `resolve_user_from_ingress`.
  - If `User` is found: Proceed as normal.
  - If `User` is `None`:
    - Send reply: "Welcome to HereCRM. Please register here: {CLERK_SIGNUP_URL}"
    - Do **not** process message as command.

### API Routes Protection

#### [MODIFY] [src/main.py](file:///home/maksym/Work/proj/HereCRM/src/main.py) or Routes

- Ensure all PWA routes (`/api/v1/pwa/*`) use `Depends(get_current_user)`.

## Verification Plan

### Automated Tests

- **Test Auth Dependency**: `tests/api/test_clerk_auth.py` (Mock JWKS, validity checks).
- **Test Webhooks**: `tests/api/routes/test_clerk_webhooks.py` (Simulate Clerk payloads).
- **Test Ingress**: `tests/api/test_ingress_flow.py` (Verify unknown number gets Invite Link).

### Manual Verification

- **Trigger Ingress**: Message from unknown number -> Verify Invite Link received.
- **Register**: Go through Clerk Flow -> Verify `User`/`Business` created in DB.
- **Login**: Log in to PWA -> Verify access to secured endpoints.
