# Tasks - Clerk Authentication for PWA

## Status

- [ ] WP01 - Foundation & Data Model
- [ ] WP02 - Authentication Service & Route Protection
- [ ] WP03 - Webhook Synchronization
- [ ] WP04 - Messaging Ingress & Registration
- [ ] WP05 - Testing & Verification

## Work Packages

### WP01 - Foundation & Data Model

**Goal**: Install dependencies, configure environment, and prepare database schema.
**Priority**: High
**Dependencies**: None

- [x] T001: Add `clerk-backend-api`, `pyjwt`, `cryptography` to `pyproject.toml` and lock.
- [x] T002: Create migration to add `clerk_id` to `users` and `clerk_org_id` to `businesses`.
- [ ] T003: Update `src/config.py` with Clerk environment variables.

### WP02 - Authentication Service & Route Protection

**Goal**: Implement verifying Clerk tokens and protecting API routes.
**Priority**: High
**Dependencies**: WP01

- [ ] T004: Implement `VerifyToken` dependency in `src/api/dependencies/clerk_auth.py` with JWKS caching.
- [ ] T005: Add JIT user/business creation logic to `VerifyToken` (fallback for webhooks).
- [ ] T006: Protect `src/api/v1/pwa` routes with `Depends(VerifyToken)`.

### WP03 - Webhook Synchronization

**Goal**: Sync User and Organization data from Clerk via Webhooks.
**Priority**: High
**Dependencies**: WP01

- [ ] T007: Create `src/api/webhooks/clerk.py` endpoint with Svix signature verification.
- [ ] T008: Implement handlers for `user.*`, `organization.*`, and `organizationMembership.*` events.

### WP04 - Messaging Ingress & Registration

**Goal**: Handle messages from unknown numbers by prompting registration.
**Priority**: Medium
**Dependencies**: WP01

- [ ] T009: Refactor `auth_service.py` to stop auto-creating users on ingress.
- [ ] T010: Update `src/api/routes.py` (webhook ingress) to reply with Clerk Signup URL if user is unknown.

### WP05 - Testing & Verification

**Goal**: Verify all auth flows and data sync integrity.
**Priority**: Medium
**Dependencies**: WP02, WP03, WP04

- [ ] T011: Create tests for Auth Dependency, Webhooks, and Ingress flow.
