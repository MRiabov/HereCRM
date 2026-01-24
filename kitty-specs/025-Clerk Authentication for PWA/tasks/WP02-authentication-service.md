---
work_package_id: WP02
title: Authentication Service & Route Protection
lane: planned
dependencies: []
subtasks: [T004, T005, T006]
---

## Objective

Implement the core authentication logic using `VerifyToken` dependency and protect PWA API routes.

## Context

We need a FastAPI dependency that extracts the Bearer token, verifies it against Clerk's JWKS, and resolves the local `User` context. If the user doesn't exist locally but has a valid token, we JIT (Just-In-Time) create them to ensure seamless experience.

## Subtasks

### T004: Implement VerifyToken Dependency

**Purpose**: Validate incoming requests.
**Steps**:

1. Create `src/api/dependencies/clerk_auth.py`.
2. Define class `VerifyToken`.
3. Constructor should load/cache JWKS from `CLERK_JWKS_URL`.
4. `__call__` method:
   - Get `Authorization` header.
   - Decode JWT using `pyjwt` and cached JWKS.
   - Validate `iss`, `exp`, `nbf`.
   - Return the decoded payload (claims) initially.

### T005: JIT User Creation Strategy

**Purpose**: Sync user if they exist in Clerk but not in DB (e.g., webhook failed/lagged).
**Steps**:

1. Enhance `VerifyToken.__call__`:
   - Extract `sub` (Clerk User ID) and `org_id` (Clerk Org ID) from claims.
   - Query `db.query(User).filter_by(clerk_id=sub).first()`.
   - **If found**: Return `User`.
   - **If NOT found**:
     - Use `clerk_backend_api` to fetch User and Organization details.
     - Create/Update `Business` with `clerk_org_id`.
     - Create `User` with `clerk_id`, email, phone.
     - Link `User` to `Business`.
     - Commit and return new `User`.
   - **Validation**: Ensure `User.business.clerk_org_id` matches token's `org_id`. Raise 403 if mismatch.

### T006: Protect API Routes

**Purpose**: Secure the PWA endpoints.
**Steps**:

1. Identify all PWA routes (e.g., `src/api/v1/pwa/`).
2. Apply `Depends(VerifyToken())` (or `get_current_user` wrapping it) to the router or individual endpoints.
3. Ensure existing `get_current_user` logic is either replaced or updated to support this new provider for PWA routes. (Legacy auth might still be needed for other parts, check scope).

## Risks

- **Performance**: JWKS fetching should be cached. User lookup on every request adds DB latency.
- **Race Conditions**: JIT creation vs Webhook creation. Use `get_or_create` logic or handle UniqueViolation errors gracefully.
