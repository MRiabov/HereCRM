---
work_package_id: "WP02"
title: "Interactive Job Completion"
lane: "for_review"
subtasks: ["T007", "T008", "T009", "T010"]
dependencies: ["WP01"]
agent: "antigravity"
shell_pid: "4166443"
---

## Objective

Implement the "done #123" command logic, allowing employees to mark jobs as completed via chat. This includes securing the command so only the assigned employee or a business owner can execute it, and updating the system prompt to recognize the intent.

## Context

The core interaction of the "Guided Workflow" is the employee simply typing "done #123" to finish a job. This triggers the status update. We must ensure this is secure and easy to use.

- **Spec**: `kitty-specs/016-Employee Guided Workflow/spec.md` (See User Story 4)
- **Data Model**: `kitty-specs/016-Employee Guided Workflow/data-model.md`
- **Contracts**: `kitty-specs/016-Employee Guided Workflow/contracts/tools.md`

## Subtasks

### T007: Implement `CompleteJobTool`

**Purpose**: Define the tool structure for the LLM to call when it detects a completion intent.
**Steps**:

1. Open `src/uimodels.py`.
2. Add `CompleteJobTool` class (verify exact fields in `contracts/tools.md`):
   - `job_id`: int
   - `notes`: Optional[str]

### T008: Implement Completion Logic (`_execute_complete_job`)

**Purpose**: Handle the database update when the tool is called.
**Steps**:

1. Open `src/tool_executor.py`.
2. Add `_execute_complete_job(tool: CompleteJobTool, user: User)`.
3. logic:
   - Fetch the job by `tool.job_id`.
   - Update status to `JobStatus.COMPLETED`.
   - Save via repository.
   - Return a success message (e.g., "Job #123 marked as completed.").

### T009: Permission Check

**Purpose**: Prevent employees from completing other people's jobs.
**Steps**:

1. In `_execute_complete_job`, before updating status:
   - Check if `user.role == UserRole.BUSINESS_OWNER`. If yes, allow.
   - If not owner, check if `job.employee_id == user.id`.
   - If neither, raise a `PermissionError` or return a "You are not assigned to this job" error message.

### T010: Update System Prompt

**Purpose**: Teach the AI to recognize "done #123".
**Steps**:

1. Open `src/services/inference_service.py`.
2. In `get_system_prompt`, add instructions:
   - "If the user says they are 'done' with a job or uses a phrase like 'done #123', call the `CompleteJobTool`."
3. Add `CompleteJobTool` to the list of available tools definitions in the prompt.

## Definition of Done

- `CompleteJobTool` is available.
- Sending "done #123" updates the database status for that job.
- Sending "done #123" for a job assigned to *someone else* fails with a permission error.
- Sending "done #123" as a business owner works for any job.

## Activity Log

- [INIT] Task generated.
- 2026-01-21T16:49:49Z – antigravity – shell_pid=4166443 – lane=doing – Started implementation via workflow command
- 2026-01-21T17:10:33Z – antigravity – shell_pid=4166443 – lane=for_review – Ready for review: Implemented CompleteJobTool with 'done #123' command, permission checks, and system prompt updates. All implementation complete and tested.
