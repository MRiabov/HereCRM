---
work_package_id: "WP03"
subtasks:
  - "T008"
  - "T009"
  - "T010"
title: "Enforcement Logic & Automation"
phase: "Phase 3 - Behavioral Enforcement"
lane: "doing"
dependencies: ["WP01"]
assignee: ""
agent: "Gemini"
shell_pid: "161109"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-22T08:25:20Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Enforcement Logic & Automation

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

- Implement "soft-blocking" to prevent tool execution when a workflow is disabled.
- Update Job logic to set correct default payment statuses.
- Validate behavior with end-to-end integration tests.

### Success Criteria

- [ ] Attempting to use `SendInvoiceTool` when invoicing is disabled returns a "soft-block" message.
- [ ] New jobs for "always paid on spot" businesses have `paid = True`.
- [ ] Integration tests verify enforcement across different business configurations.

## Context & Constraints

- Prerequisites: WP01 (Settings Service).
- Enforcement should be user-friendly: explain *why* the tool is blocked and how to re-enable it.
- Model logic: `workflow_payment_timing == 'always_paid_on_spot'` => `Job.paid = True`.

## Subtasks & Detailed Guidance

### Subtask T008 – Implement soft-blocking in `src/tool_executor.py`

- **Purpose**: Prevent use of disabled features.
- **Steps**:
    1. Update the tool execution logic (interceptor or pre-check).
    2. Check the current business's workflow settings.
    3. Block execution if:
        - `SendInvoiceTool` (and similar) AND `workflow_invoicing == 'never'`.
        - `SendQuoteTool` (and similar) AND `workflow_quoting == 'never'`.
        - Payment Tools AND `workflow_payment_timing == 'always_paid_on_spot'`.
    4. Return message: "Invoicing is currently disabled in your business settings. (Owner can re-enable this by saying 'update workflow settings')."
- **Files**: `src/tool_executor.py`

### Subtask T009 – Update Job creation logic in `src/services/crm.py`

- **Purpose**: Automate payment tracking based on business model.
- **Steps**:
    1. Locate the job creation/save logic.
    2. Retrieve business workflow setting for `payment_timing`.
    3. If `always_paid_on_spot`:
        - Set `job.paid = True` by default during creation.
- **Files**: `src/services/crm.py`

### Subtask T010 – Add integration tests for enforcement logic

- **Purpose**: End-to-end validation of the "IRL" scenarios.
- **Steps**:
    1. Create `tests/integration/test_workflow_enforcement.py`.
    2. Test Case: "Irish Window Cleaner" (Never Invoice, Spot Paid).
        - Configure settings.
        - Attempt to send invoice -> verify blocked.
        - Add job -> verify `paid = True`.
    3. Test Case: "US Contractor" (Automatic Invoicing).
        - Configure settings.
        - Verify tools are NOT blocked.
- **Files**: `tests/integration/test_workflow_enforcement.py`

## Test Strategy

- **Test Command**: `pytest tests/integration/test_workflow_enforcement.py`
- **Manual Test**: Set business to "Never Invoice" and try to tell the agent "Send an invoice to John". Verify the response.

## Definition of Done Checklist

- [ ] All subtasks completed and validated
- [ ] Integration tests pass
- [ ] `tasks.md` updated with status change

## Activity Log

- 2026-01-22T08:25:20Z – system – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-22T10:45:02Z – Gemini – shell_pid=161109 – lane=doing – Started implementation via workflow command
