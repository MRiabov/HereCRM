# Research & Decisions

**Feature**: Strict Tool-Level RBAC

## Audit: Tool Classification

We need to classify all existing tools into the new roles.

| Tool Name | Role Required | Reasoning |
|-----------|---------------|-----------|
| `AddJobTool` | EMPLOYEE | Core operational task. |
| `AddLeadTool` | EMPLOYEE | Core operational task. |
| `EditCustomerTool` | EMPLOYEE | Core operational task. |
| `ScheduleJobTool` | EMPLOYEE | Core operational task. |
| `AddRequestTool` | EMPLOYEE | Core operational task. |
| `SearchTool` | EMPLOYEE | Core operational task. |
| `CheckETATool` | EMPLOYEE | Core operational task. |
| `LocateEmployeeTool` | MANAGER | Employee privacy/management. |
| `AssignJobTool` | MANAGER | Dispatching task. |
| `ShowScheduleTool` | MANAGER | Team oversight. |
| `GetPipelineTool` | MANAGER | Business oversight. |
| `SendStatusTool` | MANAGER | Messaging control. |
| `UpdateCustomerStageTool` | MANAGER | Pipeline management. |
| `MassEmailTool` | MANAGER | Campaign management. |
| `ConvertRequestTool` | MANAGER | Operational decision. |
| `UpdateSettingsTool` | OWNER | Config changes are risky. |
| `AddServiceTool` | OWNER | Catalog management (pricing). |
| `EditServiceTool` | OWNER | Catalog management (pricing). |
| `DeleteServiceTool` | OWNER | Catalog management (pricing). |
| `GetBillingStatusTool` | OWNER | Financial info. |
| `RequestUpgradeTool` | OWNER | Financial impact. |
| `SendInvoiceTool` | OWNER | Financial operation (though Managers might need this, spec says "exporting all customers... sending invoices" is restricted). |
| `ExportQueryTool` | OWNER | Data exfiltration risk. |
| `ManageEmployeesTool` | OWNER | User management. |

*Note: `HelpTool` is special; it's available to all, but the *content* it returns is filtered.*

## Decision: RBAC Implementation Strategy

**Decision**: Use a dedicated `RBACService` class loaded with `rbac_tools.yaml`.
**Rationale**:

1. **Centralization**: All rules in one place.
2. **Extensibility**: Easy to add "Team Lead" later.
3. **Testability**: Can unit test the service without mocking the entire `ToolExecutor`.

## Decision: Database Migration

**Decision**: Rename `MEMBER` to `EMPLOYEE` in `UserRole` enum.
**Rationale**: `MEMBER` is vague. `EMPLOYEE` is explicit and matches the spec.
**Migration Plan**:

1. Update Python Enum.
2. Alembic migration to alter type (Postgres ENUM modification is tricky, might need temporary column or direct SQL `ALTER TYPE`).
