---
work_package_id: "WP02"
subtasks:
  - "T005"
  - "T006"
  - "T007"
title: "Settings Management Tooling"
phase: "Phase 2 - Settings Management"
lane: "planned"
dependencies: ["WP01"]
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-22T08:25:20Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Settings Management Tooling

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

- Implement the `UpdateWorkflowSettingsTool` for conversational workflow updates.
- Enforce RBAC (only OWNERs can update).
- Validate service and tool logic with unit tests.
- Document settings in the Assistant's manual.

### Success Criteria

- [ ] `UpdateWorkflowSettingsTool` allows updating any of the 6 settings.
- [ ] Tool returns error if called by a non-OWNER user.
- [ ] Unit tests cover various update scenarios and permission checks.
- [ ] `manual.md` reflects the new workflow controls.

## Context & Constraints

- Prerequisites: WP01 (Model and Service foundation).
- Contracts: `kitty-specs/019-business-workflow-defaults/contracts/settings.md`.
- RBAC: Check `user.role == 'OWNER'` before allowing updates.

## Subtasks & Detailed Guidance

### Subtask T005 – Implement `UpdateWorkflowSettingsTool` in `src/tools/settings.py`

- **Purpose**: Enable conversational updates to workflow configuration.
- **Steps**:
    1. Define `UpdateWorkflowSettingsTool` following the contract.
    2. Implement logic:
        - Verify current user has `role == 'OWNER'`.
        - Validate input values against Enums.
        - Use `WorkflowSettingsService.update_settings` to persist changes.
        - Return a success message describing what was changed (e.g., "Invoicing setting updated to 'never'. Quotes and invoices will now be hidden.").
- **Files**: `src/tools/settings.py`

### Subtask T006 – Add unit tests for `WorkflowSettingsService` and settings tools

- **Purpose**: Ensure logic correctness and prevent regressions.
- **Steps**:
    1. Create/update `tests/unit/test_workflow_settings.py`.
    2. Test suite should include:
        - `get_settings` returns defaults for empty business.
        - `update_settings` persists values correctly.
        - `UpdateWorkflowSettingsTool` permission check (OWNer vs Employee).
        - Value validation (rejection of invalid enum strings).
- **Files**: `tests/unit/test_workflow_settings.py`

### Subtask T007 – Update `manual.md` with workflow settings documentation

- **Purpose**: Inform the Assistant how to use and explain these settings.
- **Steps**:
    1. Update `docs/manual.md` (or equivalent location for Assistant knowledge).
    2. Add a section: "Workflow Settings".
    3. Describe each of the 6 settings and how they impact system behavior.
    4. Mention that only owners can change them.
- **Files**: `docs/manual.md`

## Test Strategy

- **Test Command**: `pytest tests/unit/test_workflow_settings.py`
- **Manual Test**: Simulate a chat request to update a setting as an owner, then as an employee.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] `tasks.md` updated with status change
- [ ] Documentation reflects changes

## Activity Log

- 2026-01-22T08:25:20Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
