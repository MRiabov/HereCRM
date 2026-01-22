---
work_package_id: "WP03"
title: "Proactive Next-Job Guide"
lane: "doing"
subtasks: ["T011", "T012", "T016", "T017"]
dependencies: ["WP02"]
agent: "Antigravity"
shell_pid: "4186310"
---

## Objective

Implement the "Proactive Guide" feature: when an employee finishes a job, the system automatically finds and prompts them with details for the *next* assigned job. This creates a continuous, guided workflow.

## Context

User Story 2: "As a Field Employee, I want the system to automatically send me the details for my next job..."
This relies on the `CompleteJobTool` from WP02 triggers this logic.

- **Spec**: `kitty-specs/016-Employee Guided Workflow/spec.md`
- **Data Model**: `kitty-specs/016-Employee Guided Workflow/data-model.md`

## Subtasks

### T011: Create `GuidedWorkflowService`

**Purpose**: Encapsulate the logic for "What is next?" and "Format message".
**Steps**:

1. Create `src/services/guided_workflow_service.py`.
2. Implement `get_next_job_for_employee(employee_id: int) -> Optional[Job]`:
   - Query pending jobs for today, ordered by scheduled time.
   - Return the first one.
3. Implement `format_next_job_message(job: Job) -> str`:
   - Format: "Next up: {Customer Name} at {Address}. \n\n[Map Link]\n\n{Reminders}"
   - Use `job.service.reminder_text` if available.
   - Generate Google Maps link from address/coordinates.

### T012: Integrate with Executor

**Purpose**: Trigger the guide after completion.
**Steps**:

1. Modify `src/tool_executor.py` -> `_execute_complete_job`.
2. After successfully engaging completion:
   - Call `GuidedWorkflowService.get_next_job_for_employee`.
   - If a next job exists, call `format_next_job_message`.
   - Append this message to the tool output string.
   - **Result**: The LLM will receive this string and can pass it on to the user, OR (better) strict tool output ensures this info is presented.

### T016: Unit Tests

**Purpose**: Verify logic for finding the correct "next" job.
**Steps**:

1. Create `tests/unit/test_guided_workflow_service.py`.
2. Test cases:
   - Employee has 0 jobs left -> returns None.
   - Employee has 2 jobs left -> returns the earlier one.
   - Employee has jobs tomorrow but none today -> returns None.
   - Message formatting includes reminder text.

### T017: Integration Test

**Purpose**: Verify the full "done" -> "next job" flow.
**Steps**:

1. Create `tests/integration/test_guided_workflow_flow.py`.
2. Scenario:
   - Seed database with employee, 2 jobs (Job A, Job B).
   - Simulate "done Job A".
   - Verify response contains details for Job B (checking for address/customer name in the string).

## Definition of Done

- completing a job returns the details of the next job in the tool output.
- Message includes Map Link and Service Reminders.
- Tests cover edge cases (no more jobs, future jobs).

## Activity Log

- [INIT] Task generated.
- 2026-01-21T17:28:42Z – Antigravity – shell_pid=4176707 – lane=doing – Started implementation via workflow command
- 2026-01-21T17:55:12Z – Antigravity – shell_pid=4176707 – lane=for_review – Done (forced): Implemented GuidedWorkflowService/NextJobLogic (as per WP prompt file). Note: tasks.md lists Scheduler tasks (T008-T010) for WP03, but prompt file listed T011-T017 which I implemented.
- 2026-01-22T06:54:57Z – Antigravity – shell_pid=4186310 – lane=doing – Started review via workflow command
