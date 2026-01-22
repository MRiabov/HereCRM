---
work_package_id: WP02
title: OAuth Infrastructure
lane: "for_review"
dependencies: []
subtasks:
- T006
- T007
- T008
- T009
- T010
agent: Cascade
shell_pid: '35736'
review_status: has_feedback
reviewed_by: MRiabov
---

## Objective

Implement the OAuth 2.0 flow to authenticate with QuickBooks Online, including secure storage, retrieval, and automated refreshing of access tokens.

## Context

We need to obtain access to the user's QuickBooks data via standard OAuth 2.0. The tokens are short-lived (1 hour) but refresh tokens last 100 days. We must handle the full lifecycle:

1. Redirect user to QuickBooks.
2. Handle callback with auth code.
3. Exchange code for tokens.
4. Store tokens securely in `credentials.db`.
5. Refresh tokens automatically when accessing the API.

## Detailed Guidance

### Subtask T006: Create QuickBooksClient wrapper

**Purpose**: detailed wrapper around `python-quickbooks` SDK to handle auth configuration.
**Files**: `src/services/accounting/quickbooks_client.py`
**Instructions**:

1. Create `QuickBooksClient` class.
2. Initialize it with Client ID, Secret, and Redirect URI from environment variables (`QB_CLIENT_ID`, `QB_CLIENT_SECRET`, `QB_REDIRECT_URI`).
3. Implement method `get_auth_url(crsf_token: str) -> str`.
4. Implement method `get_auth_client(realm_id, access_token, refresh_token)` that returns an authorized `QuickBooks` client instance.

### Subtask T007: Implement QuickBooksAuth service

**Purpose**: Handle the business logic of the OAuth flow.
**Files**: `src/services/accounting/quickbooks_auth.py`
**Instructions**:

1. Create `QuickBooksAuthService` class.
2. `generate_auth_url(business_id: int) -> str`:
    - Generate a state/CSRF token (embed business_id securely or store state mapping).
    - Call `QuickBooksClient.get_auth_url`.
3. `handle_callback(auth_code: str, realm_id: str, state: str)`:
    - Validate state.
    - Exchange `auth_code` for tokens.
    - Return the token data dict.

### Subtask T008: Implement secure token storage and retrieval logic

**Purpose**: Save the token data to the encrypted database.
**Files**: `src/services/accounting/quickbooks_auth.py`
**Instructions**:

1. Extend `QuickBooksAuthService` with `save_credentials(business_id, token_data)`:
    - Upsert `QuickBooksCredential` in `credentials_db`.
    - Update `Business.quickbooks_connected = True` in main DB.
2. Implement `get_credentials(business_id)`:
    - Retrieve from `credentials_db`.
    - Return `QuickBooksCredential` object or None.
3. Implement `disconnect(business_id)`:
    - Delete from `credentials_db`.
    - Set `Business.quickbooks_connected = False` in main DB.

### Subtask T009: Implement proactive token refresh logic

**Purpose**: Ensure valid tokens before any API call.
**Files**: `src/services/accounting/quickbooks_auth.py`
**Instructions**:

1. Implement `ensure_active_token(credential) -> credential`:
    - Check if `credential.token_expiry` is within 5 minutes of now.
    - If expiring/expired, call `python-quickbooks` refresh method.
    - Update new tokens in `credentials_db`.
    - Return valid credential.

### Subtask T010: Add OAuth flow integration tests

**Purpose**: Verify the flow works (mocking the actual QB network calls).
**Files**: `tests/integration/test_quickbooks_auth.py`
**Instructions**:

1. Mock `QuickBooksClient` network methods.
2. Test `generate_auth_url`.
3. Test `handle_callback` flow:
    - Verify credentials are saved to DB.
    - Verify Business status is updated.
4. Test `ensure_active_token` refreshes when needed.

## Definition of Done

- OAuth flow logic is complete.
- Tokens are securely stored and retrieved.
- Auto-refresh logic logic is implemented and tested.
- Integration tests pass.

## Verification

- Run `pytest tests/integration/test_quickbooks_auth.py` -> All pass.

## Activity Log

- 2026-01-22T07:51:08Z – Cascade – shell_pid=34972 – lane=doing – Started review via workflow command
- 2026-01-22T07:55:03Z – Cascade – shell_pid=34972 – lane=planned – Moved to planned
- 2026-01-22T07:58:27Z – Cascade – shell_pid=34972 – lane=planned – Moved to planned
- 2026-01-22T08:01:16Z – Cascade – shell_pid=35736 – lane=doing – Started implementation via workflow command
- 2026-01-22T09:31:42Z – Cascade – shell_pid=35736 – lane=for_review – Ready for review: Implementation of QuickBooks OAuth flow, secure credential storage, and proactive token refresh with integration tests.
