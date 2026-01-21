---
work_package_id: "WP02"
title: "Interactive Job Completion"
lane: "planned"
subtasks: ["T004", "T005", "T006", "T007"]
dependencies: ["WP01"]
---

## Objective

Implement the core interactive component of the guided workflow: the "done" command. When an employee marks a job as complete, the system should automatically provide the details and navigation for their next assigned task.

## Context

The employee finishes a job and sends "done #123". The system updates the status and immediately replies with: "Job #123 completed. Next stop: [Customer] at [Address]..."

- **Spec**: `kitty-specs/016-Employee Guided Workflow/spec.md`
- **Data Model**: `kitty-specs/016-Employee Guided Workflow/data-model.md`

## Subtasks

### T004: Add `CompleteJobTool` to `uimodels.py`

**Purpose**: Define the data structure for the job completion command.
**Steps**:

1. Open `src/uimodels.py`.
2. Define `CompleteJobTool(BaseModel)` with:
    - `job_id`: int (The ID of the job to complete).
    - `notes`: Optional[str] (Any notes provided by the employee).
3. Add a descriptive docstring to help the LLM understand when to call this tool (e.g., "Mark a job as finished or complete").

**Files**:

- `src/uimodels.py`

### T005: Create reusable `format_job_details` utility

**Purpose**: Centralize the logic for formatting job details for WhatsApp/SMS.
**Steps**:

1. Create `src/utils/formatting.py`.
2. Implement `format_job_details(job: Job) -> str`.
3. The output should follow this structure:

    ```
    Next Stop: [Customer Name]
    📍 [Address]
    🗺️ [Google Maps Link]
    📞 [Phone Number (tel link)]
    ⚡ Reminders: [Service.reminder_text entries]
    ```

4. Handle geocoding for the Maps link: if `lat/lng` are present, use them; otherwise, use the address string as a search query.

**Files**:

- `src/utils/formatting.py`

### T006: Implement `CompleteJobToolExecutor`

**Purpose**: Execute the status update logic in the tool dispatcher.
**Steps**:

1. Open `src/tool_executor.py`.
2. Register `CompleteJobTool` in the tool mapping.
3. Implement `_execute_complete_job(tool_call, current_user)`:
    - Verify the job exists and is assigned to the `current_user` (or the user is an owner).
    - Update `job.status` to 'completed' via `JobRepository`.
    - Retrieve the next job for the same employee for Today (where status is 'scheduled' or 'pending').

**Files**:

- `src/tool_executor.py`

### T007: Integrate next-job push logic

**Purpose**: Return the next job details as the primary tool response.
**Steps**:

1. In `_execute_complete_job`:
    - If a next job is found, call `format_job_details(next_job)`.
    - Return a response like: "Job #[ID] marked as done. \n\n[Formatted Next Job Details]".
    - If no more jobs: return "Job #[ID] marked as done. You are all set for the day!".

**Files**:

- `src/tool_executor.py`

## Definition of Done

- [ ] "done #123" correctly triggers `CompleteJobTool`.
- [ ] Job #123 status is updated to 'completed' in the database.
- [ ] The system replies with next job details immediately.
- [ ] The reply includes a valid Google Maps link and customer contact info.
- [ ] Service reminders are correctly included in the push message.
- [ ] Integration test passes for the full completion -> next job sequence.

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```
