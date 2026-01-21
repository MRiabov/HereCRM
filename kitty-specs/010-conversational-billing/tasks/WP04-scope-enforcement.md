---
work_package_id: "WP04"
subtasks:
  - "T017"
  - "T018"
  - "T019"
title: "Scope Enforcement"
phase: "Phase 5 - Security & Monetization"
lane: "done"
dependencies: ["WP00", "WP03"]
agent: "Antigravity"
shell_pid: "3877841"
reviewed_by: "MRiabov"
review_status: "approved"
history:
  - timestamp: "2026-01-20T14:45:30Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Scope Enforcement

## Objectives & Success Criteria

- Protect premium tools by enforcing subscription scopes.
- Ensure only businesses with the correct addons can execute specific tools.

## Context & Constraints

- Integrates into the `ToolExecutor`.
- Relies on the `active_addons` field in the `Business` model.

## Subtasks & Detailed Guidance

### Subtask T017 – Add scope metadata to tools

- **Purpose**: Annotate tools with their required permissions.
- **Steps**:
  1. Add optional `required_scope` field to the tool registry or base class.
  2. For the first premium tool (e.g., `MassEmailTool` or `ManageEmployeesTool`), set the appropriate scope string matching `billing_config.yaml`.
- **Files**: `src/uimodels.py`, `src/tool_executor.py`

### Subtask T018 – Implement enforcement in ToolExecutor

- **Purpose**: Intercept tool execution to check permissions.
- **Steps**:
  1. In `ToolExecutor.execute`, retrieve the business associated with the request.
  2. Check if the tool has a `required_scope`.
  3. If yes, verify that the `business.active_addons` list contains that scope.
  4. If missing, block execution and return a standard "permission denied" or "upgrade required" message.
- **Files**: `src/tool_executor.py`

### Subtask T019 – Verify enforcement with tests

- **Purpose**: Ensure the gatekeeper logic is robust.
- **Steps**:
  1. Create `tests/test_scope_enforcement.py`.
  2. Test a "free" business trying to call a scoped tool (should fail).
  3. Test a "paid" business (with addon) calling the same tool (should succeed).
- **Files**: `tests/test_scope_enforcement.py`

## Risks & Mitigations

- **Bypass**: Ensure *all* tool execution paths go through the enforcement logic.
- **Performance**: Scope checks should be fast (local list check).

## Definition of Done Checklist

- [x] Tool metadata includes scopes
- [x] `ToolExecutor` blocks unauthorized calls
- [x] User receives helpful upgrade prompt when blocked
- [x] Automated tests cover authorized/unauthorized scenarios

## Review Guidance

- Verify that the error message received when blocked is helpful and encourages the user to use the "billing" command to upgrade.
- Check that standard/free tools remain accessible without issues.

## Activity Log

- 2026-01-20T14:45:30Z – antigravity – lane=planned – Prompt created.
- 2026-01-20T19:05:37Z – Antigravity – shell_pid=3877841 – lane=doing – Started implementation via workflow command
- 2026-01-20T20:25:32Z – Antigravity – shell_pid=3877841 – lane=done – Review passed: Scope enforcement implemented and verified.
