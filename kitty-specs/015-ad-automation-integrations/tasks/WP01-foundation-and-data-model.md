---
work_package_id: "WP01"
title: "Foundation & Data Model"
lane: "done"
subtasks: ["T001", "T002", "T003", "T004", "T005"]
dependencies: []
agent: "Antigravity"
shell_pid: "4073129"
reviewed_by: "MRiabov"
review_status: "approved"
---

## Objective

Establish the database foundation and core service layer for Ad Automation Integrations. This WP focuses on the `IntegrationConfig` entity, which stores API Keys and webhook settings, and the basic repository/service logic to manage them.

## Context

We need a secure way to store integration credentials (API keys, Meta Access Tokens, Webhook URLs).

- **Spec**: `kitty-specs/015-ad-automation-integrations/spec.md`
- **Data Model**: `kitty-specs/015-ad-automation-integrations/data-model.md`

## Subtasks

### T001: Create alembic migration for `integration_configs`

**Purpose**: Create the database table to store configuration.
**Steps**:

1. Run `alembic revision -m "add_integration_configs_table"`.
2. Define the table `integration_configs`:
    - `id`: UUID, Primary Key.
    - `type`: String (Enum: `INBOUND_KEY`, `META_CAPI`, `WEBHOOK`).
    - `label`: String, Nullable (Friendly name).
    - `key_hash`: String, Nullable (Indexed). Used for authenticating `INBOUND_KEY`.
    - `config_payload`: JSONB. Stores provider specific settings.
    - `is_active`: Boolean, Default `True`.
    - `created_at`, `updated_at`: DateTime.

### T002: Implement `IntegrationConfig` SQLAlchemy model

**Purpose**: Map the table to a Python class.
**Steps**:

1. Create `src/models/integration_config.py`.
2. Define `IntegrationConfig` class inheriting from `Base`.
3. Define `IntegrationType` Enum (`INBOUND_KEY`, `META_CAPI`, `WEBHOOK`).
4. Ensure all fields from T001 are mapped.

### T003: Create `IntegrationRepository`

**Purpose**: Data access layer for configurations.
**Steps**:

1. Create `src/repositories/integration_repository.py`.
2. Implement `create(config)`: Save new config.
3. Implement `get_by_id(id)`: Retrieve by UUID.
4. Implement `get_active_by_type(type)`: Return list of active configs for a given type (e.g., all active WEBHOOKs).
5. Implement `get_by_key_hash(hash)`: specific lookup for authentication.

### T004: Implement `IntegrationService` base

**Purpose**: Core logic, specifically handling API Key generation and hashing.
**Steps**:

1. Create `src/services/integration_service.py`.
2. Implement `generate_api_key() -> str`: Generate a secure random string (e.g., using `secrets` module, 'sk_live_...').
3. Implement `hash_key(key: str) -> str`: SHA-256 hash the key for storage/lookup.
4. Implement `create_inbound_integration(label) -> (config, raw_key)`:
    - Generate key.
    - Hash it.
    - Save config with `type=INBOUND_KEY` and `key_hash`.
    - Return the raw key (to be shown to user ONCE) and the config object.

### T005: Add unit tests

**Purpose**: Verify the foundation.
**Steps**:

1. Create `tests/unit/test_integration_service.py`.
2. Test `generate_api_key` produces unique/random strings.
3. Test `hash_key` is consistent.
4. Create `tests/unit/test_integration_repository.py`.
5. Test CRUD operations and lookups using a DB session fixture.

## Definition of Done

- `integration_configs` table exists.
- `IntegrationConfig` model is importable.
- `IntegrationRepository` can save and retrieve configs.
- `IntegrationService` can generate and hash keys.
- All unit tests pass.

## Activity Log

- 2026-01-21T13:31:18Z – Antigravity – shell_pid=4073129 – lane=doing – Started implementation via workflow command
- 2026-01-21T14:20:04Z – Antigravity – shell_pid=4073129 – lane=for_review – Ready for review: Established database foundation (IntegrationConfig) and core service layer for API key management. Includes Alembic migration and unit tests.
- 2026-01-22T12:39:16Z – Antigravity – shell_pid=4073129 – lane=done – Review passed: Foundation and Data Model for integrations implemented and verified.
