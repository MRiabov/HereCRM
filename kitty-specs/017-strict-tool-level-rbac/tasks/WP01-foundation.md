---
work_package_id: "WP01"
title: "RBAC Foundation & Service"
lane: "planned"
dependencies: []
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
---

# WP01: RBAC Foundation & Service

## Context

We are implementing a strict Role-Based Access Control (RBAC) system for all LLM executable tools. This work package lays the groundwork: defining roles, creating the configuration file, and building the service that checks permissions.

## Objective

Update the `UserRole` enum, create the `rbac_tools.yaml` configuration, and implement the `RBACService` capable of verifying if a role can access a tool.

## Subtasks

### T001: Create RBAC Configuration

**Goal**: Create the single source of truth for tool permissions.

- Create `src/assets/rbac_tools.yaml`.
- Populate it with the mapping defined in `data-model.md`.
- Ensure all tools mentioned in the spec are included with their `friendly_name` and minimum `role`.
- **Note**: The hierarchy is Owner > Manager > Employee. If a tool is `employee`, everyone can use it. If `manager`, only Manager and Owner.

### T002: Update UserRole Enum

**Goal**: Update the application's role definitions.

- Modify `src/models.py` (or where `UserRole` is defined).
- Rename `MEMBER` to `EMPLOYEE`.
- Add `MANAGER`.
- Ensure `OWNER` remains.
- Update any obvious references in `src/models.py` if needed.

### T003: Database Migration

**Goal**: Persist the enum change in the database.

- Create a new Alembic revision: `alembic revision -m "update_user_roles"`.
- **Crucial**: PostgreSQL enums require explicit SQL to update values.
- In `upgrade()`:
  - Rename the enum value 'member' to 'employee' if using `ALTER TYPE ... RENAME VALUE`.
  - Add 'manager' value: `ALTER TYPE userrole ADD VALUE 'manager'`.
  - Or handle it by creating a new type, converting columns, and dropping the old type (safer).
- In `downgrade()`: Reverse the changes.

### T004: Implement RBACService

**Goal**: Create the service logic for permission checking.

- Create `src/services/rbac_service.py`.
- Class `RBACService`.
- **Initialization**: Load `src/assets/rbac_tools.yaml` (cache it, don't read on every call).
- **Method**: `check_permission(self, user_role: UserRole, tool_name: str) -> bool`
  - Normalize `tool_name` (e.g., match class name).
  - Look up the required role for the tool.
  - Return `True` if `user_role` >= `required_role`.
  - Return `False` otherwise.
- **Method**: `get_tool_config(self, tool_name: str) -> dict`
  - Returns `{'role': ..., 'friendly_name': ...}` or None if not protected.
- **Hierarchy logic**:
  - Owner (3) covers everything.
  - Manager (2) covers Manager & Employee tools.
  - Employee (1) covers Employee tools only.

### T005: Unit Tests for RBACService

**Goal**: Verify the logic is sound.

- Create `tests/unit/test_rbac_service.py`.
- Test cases:
  - Employee can access employee tools.
  - Employee cannot access manager/owner tools.
  - Manager can access employee & manager tools.
  - Manager cannot access owner tools.
  - Owner can access everything.
  - Unknown tools (fail safe or pass through? Spec implies strictness, so maybe fail or warn. Assume default deny if not in config, or verify spec intent. Spec says "All tools... are now scoped". Best to default to strict or handle gracefully).
  - Test `get_tool_config` returns correct friendly names.

## Definition of Done

- `rbac_tools.yaml` exists and is populated.
- `UserRole` has the correct 3 values.
- DB migration runs successfully.
- `RBACService` is implemented and unit tests pass.
