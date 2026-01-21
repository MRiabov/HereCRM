# Implementation Plan: Strict Tool-Level RBAC

*Path: kitty-specs/017-strict-tool-level-rbac/plan.md*

**Branch**: `017-strict-tool-level-rbac` | **Date**: 2026-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/017-strict-tool-level-rbac/spec.md`

## Summary

This feature implements a strict Role-Based Access Control (RBAC) system for all LLM-callable tools. It introduces three distinct user roles (`OWNER`, `MANAGER`, `EMPLOYEE`) and enforces permissions at the tool execution layer. Additionally, it ensures the assistant persona respects data access boundaries by appending disclaimers when non-owners ask about restricted topics.

Key components:

1. **Role Hierarchy**: Updating `UserRole` enum to support OWNER, MANAGER, EMPLOYEE.
2. **RBAC Configuration**: A centralized `rbac_tools.yaml` file defining which roles can access which tools.
3. **Execution Interceptor**: Logic in `ToolExecutor` (or a new service) to intercept tool calls and verify permissions against the active user's role and business entitlements.
4. **Persona Enforcement**: Logic in `WhatsappService` to append disclaimers for non-owner queries on restricted topics, especially via `HelpTool`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: SQLAlchemy (ORM), Pydantic (validation), PyYAML (config)
**Storage**: PostgreSQL (Users table update)
**Project Type**: Single backend service (FastAPI)

**Key Technical Decisions**:

- **Role Storage**: The existing `UserRole` enum in `src/models.py` will be updated. `MEMBER` will be renamed to `EMPLOYEE`. `MANAGER` will be added.
- **Config Source**: Permissions will be hardcoded in `src/assets/rbac_tools.yaml` to ensure they are version-controlled and audit-friendly.
- **Enforcement Point**: The `ToolExecutor.execute()` method is the choke point for all tool calls. It will query an `RBACService` (to be created) which checks both:
    1. **Business Entitlements**: Does the business have the addon? (Existing logic, to be formalized).
    2. **User Role**: Does the user have the required role for this tool? (New logic).
- **Persona Disclaimer**: Specifically for `HelpTool` or free-form QA, if an employee asks about a restricted topic (e.g., billing), the answer will be refused or disclaimed. This logic will reside in `WhatsappService` or `HelpService`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **LLM-First Text Processing**: Compliant. We are not hardcoding text rules for the *content* of the query, but we are enforcing hard permissions on the *tools* the LLM selects. This aligns with safety.
- **Intent Transparency**: Compliant. When a tool is blocked, the user gets a clear "Permission Denied" message explaining why (FR-005).
- **Progressive Documentation**: We will need to update `src/assets/manual.md` to explain the new roles so the assistant knows about them.

## Project Structure

### Documentation (this feature)

```
kitty-specs/017-strict-tool-level-rbac/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```
src/
├── models.py                  # UserRole enum update
├── tool_executor.py           # Tool execution interception
├── services/
│   ├── rbac_service.py        # New service for permission logic
│   └── whatsapp_service.py    # Persona disclaimer logic
└── assets/
    └── rbac_tools.yaml        # New config file
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New Service (`RBACService`) | Decouple permission logic from execution | Hardcoding checks in `ToolExecutor` leads to spaghetti code as rules grow (business vs. user role). |
| YAML Config | Auditability and visibility of permissions | Decorators on tool classes scatter permissions across the codebase, making it hard to audit the security posture in one view. |
