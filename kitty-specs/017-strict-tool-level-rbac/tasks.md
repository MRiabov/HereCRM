# Tasks: Strict Tool-Level RBAC

*Spec: [spec.md](spec.md)*
*Status: Planned*

## Work Packages

### WP01: RBAC Foundation & Service

**Goal**: Establish the role hierarchy, configuration, and the core RBAC service.
**Priority**: High
**Dependencies**: None

- [ ] **T001**: Create `src/assets/rbac_tools.yaml` with the complete tool-to-role mapping.
- [ ] **T002**: Update `UserRole` enum in `src/models.py` (MEMBER -> EMPLOYEE, add MANAGER).
- [ ] **T003**: Create Alembic migration to update the `userrole` enum type in PostgreSQL.
- [ ] **T004**: Implement `RBACService` in `src/services/rbac_service.py` to load config and verify permissions.
- [ ] **T005**: Add unit tests for `RBACService` covering all role hierarchies.

### WP02: Tool Execution Enforcement

**Goal**: Intercept all tool executions and enforce RBAC rules.
**Priority**: High
**Dependencies**: WP01

- [ ] **T006**: Inject `RBACService` into `ToolExecutor` and intercept `execute` calls.
- [ ] **T007**: Implement the standard "Permission Denied" response format using friendly names.
- [ ] **T008**: Add integration tests verifying blocked/allowed access for different roles.

### WP03: Persona & Documentation

**Goal**: Enforce assistant persona disclaimers and update documentation.
**Priority**: Medium
**Dependencies**: WP02

- [ ] **T009**: Modify `WhatsappService` (or equivalent) to append the "status disclaimer" for non-OWNERs on restricted topics.
- [ ] **T010**: Add tests ensuring the disclaimer appears only when required.
- [ ] **T011**: Update `src/assets/manual.md` to reflect the new `MANAGER` and `EMPLOYEE` roles.
