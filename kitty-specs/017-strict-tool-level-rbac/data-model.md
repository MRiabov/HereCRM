# Data Model Changes

## User Entity

### `UserRole` Enum Update

The `UserRole` enum in `src/models.py` will be updated to support the new hierarchy.

```python
class UserRole(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    EMPLOYEE = "employee"  # Renamed from MEMBER
```

### Database Schema

- **Table**: `users`
- **Column**: `role`
- **Change**: Update enum values in database (PostgreSQL enum `userrole`).

## Configuration Data

### `src/assets/rbac_tools.yaml`

This file will serve as the source of truth for tool permissions.

```yaml
# RBAC Configuration
# Maps tool class names to the minimum role required to execute them.
# Roles: owner > manager > employee

tools:
  # Employee Level (Bottom tier - Execution)
  AddJobTool:
    role: employee
    friendly_name: "add a job"
  AddLeadTool:
    role: employee
    friendly_name: "add a lead"
  EditCustomerTool:
    role: employee
    friendly_name: "edit customer details"
  ScheduleJobTool:
    role: employee
    friendly_name: "schedule a job"
  AddRequestTool:
    role: employee
    friendly_name: "log a request"
  SearchTool:
    role: employee
    friendly_name: "search capabilities"
  CheckETATool:
    role: employee
    friendly_name: "check ETA"
  CreateQuoteInput:
    role: employee
    friendly_name: "create a quote"

  # Manager Level (Mid tier - Oversight)
  LocateEmployeeTool:
    role: manager
    friendly_name: "locate employees"
  AssignJobTool:
    role: manager
    friendly_name: "assign jobs"
  ShowScheduleTool:
    role: manager
    friendly_name: "view full schedule"
  GetPipelineTool:
    role: manager
    friendly_name: "view pipeline"
  SendStatusTool:
    role: manager
    friendly_name: "send status updates"
  UpdateCustomerStageTool:
    role: manager
    friendly_name: "update pipeline stages"
  ConvertRequestTool:
    role: manager
    friendly_name: "convert requests"
  MassEmailTool:
    role: manager
    friendly_name: "send mass emails"

  # Owner Level (Top tier - Admin/Finance/Risk)
  UpdateSettingsTool:
    role: owner
    friendly_name: "modify settings"
  AddServiceTool:
    role: owner
    friendly_name: "add services"
  EditServiceTool:
    role: owner
    friendly_name: "edit services"
  DeleteServiceTool:
    role: owner
    friendly_name: "delete services"
  GetBillingStatusTool:
    role: owner
    friendly_name: "check billing"
  RequestUpgradeTool:
    role: owner
    friendly_name: "request upgrades"
  SendInvoiceTool:
    role: owner
    friendly_name: "send invoices"
  ExportQueryTool:
    role: owner
    friendly_name: "export data"
  ManageEmployeesTool:
    role: owner
    friendly_name: "manage employees"
  ExitDataManagementTool:
    role: owner
    friendly_name: "manage data"
```
