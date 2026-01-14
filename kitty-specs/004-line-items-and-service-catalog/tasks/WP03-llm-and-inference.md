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
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-14T19:10:01Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

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
