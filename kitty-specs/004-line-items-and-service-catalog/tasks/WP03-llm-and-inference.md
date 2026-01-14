---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "LLM & Line Item Inference"
phase: "Phase 2 - Feature Development"
lane: "planned"
assignee: ""
agent: "antigravity"
shell_pid: ""
review_status: "has_feedback"
reviewed_by: "antigravity"
history:
  - timestamp: "2026-01-14T19:10:01Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-14T20:57:12Z"
    lane: "for_review"
    agent: "system"
    shell_pid: ""
    action: "Ready for review"
  - timestamp: "2026-01-14T21:15:00Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Review complete: Needs changes due to failing tests and stale state issues"
---

## Review Feedback

**Status**: ❌ **Needs Changes**

**Key Issues**:

1. **Failing Test**: `tests/test_inference_logic.py::test_tool_executor_with_line_items` fails with `assert None == 110.0`. The `Job.value` is not correctly reflected in the job object after line items are added.
2. **Stale Object State**: The event listener in `src/repositories.py` (lines 376-397) uses a direct SQL `UPDATE` during `after_insert`/`after_update` of `LineItem`. While this updates the database, it does NOT update the `Job` object currently in the SQLAlchemy session's identity map. This leads to stale data (`None` or old value) throughout the rest of the transaction.
3. **Inference / ToolExecutor Race**: If both `tool.price` and `tool.line_items` are provided, the `Job` is initialized with `tool.price` first, then line items are added. The listener aims to overwrite the value, but the inconsistency between the object state and DB can cause issues.

**What Was Done Well**:

- `InferenceService` logic is solid and covers all requested scenarios.
- LLM system instructions are clear and provide helpful examples.
- Data models and Pydantic schemas are correctly implemented.

**Action Items**:

- [ ] Fix `Job.value` synchronization to ensure the `Job` object in the session is updated or refreshed.
- [ ] ensure all tests in `tests/test_inference_logic.py` pass.
- [ ] Verify that adding a job with BOTH a top-level price and specific line items results in a consistent `Job.value`.

# Work Package Prompt: WP03 – LLM & Line Item Inference

## Objectives & Success Criteria

- Update the LLM's understanding of jobs to include structured line items.
- Implement intelligent inference logic to fill in missing quantities or unit prices based on catalog defaults and user-provided totals.
- Achievement: Natural language commands like "Window Clean, $50" correctly resolve to a structured line item with quantity inferred from the catalog.

## Context & Constraints

- Modifies the `AddJobTool` schema.
- Requires changes to the LLM system instructions in `llm_client.py`.
- Must handle cases where no catalog service matches (fallback to ad-hoc items).

## Subtasks & Detailed Guidance

### Subtask T010 – Update `AddJobTool` schema

- **Purpose**: Allow the LLM to provide line items in its tool call.
- **Steps**:
  - Update the Pydantic model (or JSON schema) for `AddJobTool` in `src/uimodels.py`.
  - Add a `line_items` field as a list of objects (description, quantity, unit_price, total_price).
- **Files**: `src/uimodels.py`
- **Parallel?**: Yes

### Subtask T011 – Update `llm_client.py`

- **Purpose**: Instruct the LLM on how to extract line items.
- **Steps**:
  - Update the system instructions to explain line item extraction.
  - Provide examples in the prompt for different scenarios (Quantity + Service, Total + Service, etc.).
- **Files**: `src/llm_client.py`
- **Parallel?**: Yes

### Subtask T012 – Update `ToolExecutor`

- **Purpose**: Process `line_items` during job creation.
- **Steps**:
  - Update `ToolExecutor.execute_add_job` to pass `line_items` to the repository.
  - Ensure inference logic is called before saving the job.
- **Files**: `src/services/tool_executor.py`
- **Parallel?**: No

### Subtask T013 – Implement inference logic

- **Purpose**: Reconcile user input with catalog defaults.
- **Steps**:
  - Implement a service or utility that takes the LLM's raw line items and matches them against the `Service` catalog.
  - If a match is found and only `total_price` is present, calculate `quantity = total_price / default_price`.
  - If `quantity` is present but no `unit_price`, set `unit_price = total_price / quantity`.
- **Files**: `src/services/inference_service.py` (New file) or `src/llm_client.py`
- **Parallel?**: No

## Risks & Mitigations

- Precision/Rounding: Ensure unit price calculations don't result in many decimal places unless necessary.
- Ambiguous matches: If multiple services match, the LLM should ideally clarify, but fallback to a reasonable default.

## Definition of Done Checklist

- [ ] `AddJobTool` includes a `line_items` list
- [ ] LLM correctly identifies line items from test phrases
- [ ] Inference logic correctly calculates missing values
- [ ] Tests covering all scenarios in `spec.md` pass

## Activity Log

- 2026-01-14T19:10:01Z – antigravity – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-14T20:57:12Z – system – shell_pid= – lane=for_review – Ready for review
