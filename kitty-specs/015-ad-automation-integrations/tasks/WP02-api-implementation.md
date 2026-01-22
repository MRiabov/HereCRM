---
work_package_id: "WP02"
title: "API Implementation"
lane: "done"
subtasks: ["T006", "T007", "T008", "T009", "T010", "T011"]
dependencies: ["WP01"]
agent: "Antigravity"
shell_pid: "4073129"
reviewed_by: "MRiabov"
review_status: "approved"
---

## Objective

Implement the public-facing API endpoints for the Integration layer. This includes the Inbound API (Leads, Requests) protected by API Keys, and the Provisioning API protected by URL signatures.

## Context

These endpoints allow external systems to push data into HereCRM.

- **Contract**: `kitty-specs/015-ad-automation-integrations/contracts/api.yaml`
- **Spec**: `kitty-specs/015-ad-automation-integrations/spec.md` (Sections 4.1, 4.2)

## Subtasks

### T006: Implement `ApiKeyAuth` dependency

**Purpose**: Secure the inbound endpoints.
**Steps**:

1. Create `src/api/dependencies/auth.py` (or add to existing).
2. Define `get_api_key_auth(header: X-API-Key)` dependency.
3. Steps inside dependency:
    - Reject missing header (401).
    - Hash the provided key (using `IntegrationService.hash_key`).
    - Query `IntegrationRepository.get_by_key_hash`.
    - If not found or `!is_active`, reject (401).
    - Return the `IntegrationConfig` object.

### T007: Implement `Signer` utility

**Purpose**: Verify signatures for the provisioning endpoint (`/provision`).
**Steps**:

1. Create `src/utils/security.py`.
2. Implement `Signer` class using `HMAC-SHA256`.
3. Method `sign(data: str, secret: str) -> str`.
4. Method `verify(data: str, signature: str, secret: str) -> bool`.
5. Note: Ideally use a system-level secret (e.g., `settings.SECRET_KEY`) for these internal provisioning links.

### T008: Implement `POST /provision` endpoint

**Purpose**: Allow secure saving of integration credentials.
**Steps**:

1. Create `src/api/v1/integrations.py`.
2. Route: `POST /api/v1/integrations/provision`.
3. Input: `auth_id` (uuid), `config_type` (Enum), `label`, `payload`.
4. Logic:
    - Verify `auth_id` is a valid signed token (or verify a signature included in the request - *Correction*: Spec implies `auth_id` itself is the token or part of the validation. Stick to: Assume `auth_id` was signed by the server when generating the setup link. Verify `auth_id` matches a known pattern or simply use `Signer` to verify the payload if applicable. *Refinement*: The spec says "Protected by auth_id signature validation". We can assume the frontend sends a signed payload or the `auth_id` is a signed JWT. For simplicity in this WP: Implement a `verify_provision_token(auth_id)` method in `IntegrationService` that validates it.)
    - If valid, create `IntegrationConfig` via `IntegrationRepository.create`.
    - Return 200.

### T009: Implement `POST /leads` endpoint

**Purpose**: Ingest leads from ads.
**Steps**:

1. Route: `POST /api/v1/integrations/leads`.
2. Auth: `Depends(get_api_key_auth)`.
3. Schema: `name` (req), `phone` (req), `email`, `source`.
4. Logic:
    - Call `CustomerService.find_or_create(phone, email, ...)` (Use existing service).
    - Return `{ "customer_id": "...", "is_existing": bool }`.

### T010: Implement `POST /requests` endpoint

**Purpose**: Ingest service requests.
**Steps**:

1. Route: `POST /api/v1/integrations/requests`.
2. Auth: `Depends(get_api_key_auth)`.
3. Schema: Customer info + `address`, `service_type`, `notes`.
4. Logic:
    - `CustomerService.find_or_create(...)`.
    - `RequestService.create_request(customer_id, address, ...)` (Use existing service).
    - Return `{ "request_id": "...", "customer_id": "..." }`.

### T011: Add integration tests

**Purpose**: Validation.
**Steps**:

1. Create `tests/integration/test_integrations_api.py`.
2. Test `POST /leads` with valid and invalid API Keys.
3. Test `POST /requests` creates DB records.
4. Test `POST /provision` with valid/invalid signatures.

## Definition of Done

- All endpoints defined in `contracts/api.yaml` are implemented.
- Endpoints are secured (API Key or Signature).
- Data is correctly persisted to `customers` and `requests` tables.
- Integration tests pass.

## Activity Log

- 2026-01-21T15:08:09Z – Antigravity – shell_pid=4073129 – lane=doing – Started implementation via workflow command
- 2026-01-21T15:40:21Z – Antigravity – shell_pid=4073129 – lane=for_review – Ready for review: Implemented API implementation including ApiKeyAuth, Signer, and endpoints for leads, requests, and provisioning. All integration tests pass.
- 2026-01-22T08:03:17Z – Antigravity – shell_pid=4073129 – lane=for_review – Ready for review: API implementation complete with all endpoints (provision, leads, requests), ApiKeyAuth dependency, Signer utility, and comprehensive integration tests. All tests passing.
- 2026-01-22T12:39:17Z – Antigravity – shell_pid=4073129 – lane=done – Review passed: API Implementation for integrations implemented and verified.
