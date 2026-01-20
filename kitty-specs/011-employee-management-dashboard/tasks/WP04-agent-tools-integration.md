---
work_package_id: WP04
title: Agent Tools & Integration
lane: planned
dependencies: []
subtasks: [T011, T012, T013, T014]
---

# Work Package 04: Agent Tools & Integration

## Objective

Expose the dashboard and assignment capabilities to the LLM agent via structured Tools. This binds the service logic (WP01/WP02) and presentation layer (WP03) into the conversational loop.

## Files

- `src/tools/employee_management.py` (New)
- `src/llm/client.py` (Modify - to register tools)
- `tests/integration/test_employee_dashboard_flow.py` (New)

## Detailed Guidance

### T011: Create Tool Definitions

**Purpose**: Define the interface for the LLM.

1. Create `src/tools/employee_management.py`.
2. Define `ShowScheduleTool`:
   - Input: None (or optional `date`).
   - Description: "Show the schedule for all employees for today."
3. Define `AssignJobTool`:
   - Input: `job_id: int`, `assign_to_name: str` (using name allows LLM to just pass what user said).
   - Description: "Assign a specific job to an employee by name."

### T012: Implement Tool Logic

**Purpose**: Connect Tools to Services.

1. In `ShowScheduleTool.run`:
   - Call `DashboardService.get_employee_schedules` and `get_unscheduled_jobs`.
   - Call `render_employee_dashboard`.
   - Return the rendered string.
2. In `AssignJobTool.run`:
   - Call `AssignmentService.find_employee_by_name`.
   - **Ambiguity Handling**:
     - If 0 matches: Return "Error: Could not find employee named X."
     - If >1 match: Return "Status: Ambiguous. Did you mean A or B?" (Let the LLM handle the re-prompting).
   - If 1 match: Call `AssignmentService.assign_job(job_id, user.id)`.
   - Return success message: "Assigned Job #123 to John Smith."

### T013: Register Tools

**Purpose**: Make them available to the bot.

1. Update `src/llm/client.py` (or wherever tools are registered).
2. Add `ShowScheduleTool` and `AssignJobTool` to the active toolset.
3. Ensure they are restricted or only relevant for Owner context (system instruction updates might be needed in a separate config, but ensure the tool code checks permissions if possible).

### T014: Integration Test

**Purpose**: Simulate end-to-end usage.

1. Create `tests/integration/test_employee_dashboard_flow.py`.
2. Scenario:
   - Setup: Create Owner, Employee, Job #99.
   - Action 1: `ShowScheduleTool` -> Verifies output shows "Unscheduled jobs: ... #99".
   - Action 2: `AssignJobTool(99, "Empl")` -> Verifies success.
   - Action 3: `ShowScheduleTool` -> Verifies "Employee's schedule: ... #99".

## Acceptance Criteria

- Tools are invokable by the agent.
- Agent successfully assigns jobs using names.
- Ambiguity is handled gracefully (not crashing).
- Full flow is verified by integration test.

## Implementation Command

`spec-kitty implement WP04 --base WP03`
