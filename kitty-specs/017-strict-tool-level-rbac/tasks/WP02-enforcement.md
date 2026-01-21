---
work_package_id: WP02
title: Tool Execution Enforcement
lane: "doing"
dependencies: []
subtasks:
- T006
- T007
- T008
agent: "Antigravity"
shell_pid: "4166443"
---

# WP02: Tool Execution Enforcement

## Context

With the `RBACService` and roles in place (from WP01), we now need to enforce these rules at the point of tool execution. This ensures that no matter how the LLM calls a tool, the permission is verified against the actual user.

## Objective

Modify `ToolExecutor` to intercept execution calls, check permissions using `RBACService`, and return a specific "Permission Denied" message if unauthorized.

## Subtasks

### T006: Intercept Execution

**Goal**: Inject security checks into the tool execution flow.

- Modify `src/tool_executor.py` (or wherever tools are executed).
- Inject `RBACService`.
- In the `execute(tool_name, arguments, user)` method (or equivalent):
  - Before running the tool logic, call `rbac_service.check_permission(user.role, tool_name)`.
  - **Note**: Ensure you have access to the `user` object in this context.

### T007: Implement Permission Denied Response

**Goal**: Return the standard user-friendly denial message.

- If `check_permission` returns `False`:
  - Fetch the friendly name using `val = rbac_service.get_tool_config(tool_name)`.
  - Construct the message: `"It seems you are trying to [friendly_name]. Sorry, you don't have permission for that."`
  - Return this string as the result of the tool execution. Do NOT raise an exception that crashes the flow; the LLM needs to see this message to explain it to the user.

### T008: Integration Tests

**Goal**: Verify end-to-end enforcement.

- Create `tests/integration/test_rbac_enforcement.py`.
- Mock `ToolExecutor` and its dependencies (or use real if feasible).
- **Scenario 1**: Employee tries to use `CheckETATool` (Allowed). verify tool runs.
- **Scenario 2**: Employee tries to use `SendInvoiceTool` (Denied). Verify returned string matches the denial format.
- **Scenario 3**: Manager tries to use `LocateEmployeeTool` (Allowed).
- **Scenario 4**: Manager tries to use `SendInvoiceTool` (Denied).
- **Scenario 5**: Owner tries `SendInvoiceTool` (Allowed).

## Definition of Done

- `ToolExecutor` enforces permissions for every call.
- Unauthorized calls result in the specific friendly error message.
- Integration tests cover all 3 roles against restricted and allowed tools.

## Activity Log

- 2026-01-21T16:49:13Z – Antigravity – shell_pid=4166443 – lane=doing – Started implementation via workflow command
