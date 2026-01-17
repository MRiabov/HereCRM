---
work_package_id: "WP05"
subtasks:
  - "T016"
  - "T017"
  - "T018"
title: "Refinement & Polish"
phase: "Phase 3 - Polish & Launch"
lane: "done"
assignee: ""
agent: "Antigravity"
shell_pid: "564ab52f"
review_status: "approved without changes"
reviewed_by: "Antigravity"
history:
  - timestamp: "2026-01-14T19:10:01Z"
    lane: "planned"
    agent: "antigravity"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP05 – Refinement & Polish

## Objectives & Success Criteria

- Ensure numerical precision and correct rounding in all calculations.
- Validate that historical data is preserved correctly.
- Implement robust validation for edge cases.

## Context & Constraints

- Financial data requires deterministic rounding (usually 2 decimal places).
- Historical snapshots are critical for accounting integrity.

## Subtasks & Detailed Guidance

### Subtask T016 – Handle rounding issues

- **Purpose**: Prevent floating point errors from affecting totals.
- **Steps**:
  - Ensure all unit price and quantity calculations are rounded to two decimal places (or appropriate precision).
  - Verify that `sum(item.total_price) == job.value`.
- **Files**: `src/services/inference_service.py`
- **Parallel?**: Yes

### Subtask T017 – Validate snapshotting

- **Purpose**: Ensure historical jobs don't change if catalog prices change.
- **Steps**:
  - Add a test case that creates a job, changes the service catalog price, and verifies the job's line item price remains the same.
- **Files**: `tests/test_line_items.py` (New file)
- **Parallel?**: No

### Subtask T018 – Add validation for edge cases

- **Purpose**: Prevent invalid data entry.
- **Steps**:
  - Add checks for negative quantities or zero prices (if not allowed).
  - Handle cases where the LLM might propose nonsensical quantities (e.g., millions).
- **Files**: `src/models.py`, `src/uimodels.py`
- **Parallel?**: Yes

## Risks & Mitigations

- Rounding divergence: Use `decimal` module if floating point inaccuracy becomes a problem.

## Definition of Done Checklist

- [x] Rounding logic implemented and tested
- [x] Snapshotting verified with tests
- [x] Edge cases handled gracefully
- [x] Final smoke test of the entire flow passes

## Activity Log

- 2026-01-14T19:10:01Z – antigravity – lane=planned – Prompt generated via /spec-kitty.tasks
- 2026-01-15T10:40:05Z – Antigravity – lane=doing – Started implementation
- 2026-01-16T18:10:03Z – Antigravity – lane=for_review – Ready for review
- 2026-01-16T18:15:00Z – Antigravity – shell_pid=564ab52f – lane=done – Approved without changes
