---
work_package_id: WP05
subtasks:
  - T018
  - T019
  - T020
lane: planned
history:
  - date: 2026-01-13
    status: planned
    agent: spec-kitty
---
# Work Package: Refinement & Productionizing

## Objective

Polish the experience, handle complex edge cases like specific scheduling updates, and ensure all success criteria are met through a final manual verification.

## Context

The core paths works, but we need to handle "Schedule..." commands which might imply finding a fuzzy match (e.g. "Schedule John" when we have a job for "John Smith"). We also need to graceful fallback for things the LLM can't parse.

## Subtasks

### T018: Scheduling Logic

- Refine `ScheduleJobTool`.
- Logic:
  - If `job_id` is not provided, search for active jobs matching `customer_name`.
  - If multiple found, ask user to clarify (or just pick latest for MVP).
  - Update the `Job` record with the new time.

### T019: Fallback to Requests

- In `LLMParser`, if the intent is unclear or parsing fails, return `StoreRequestTool`.
- This ensures no data is lost; it just goes into the "Requests" bucket for manual review.

### T020: Final E2E Walkthrough

- Perform the manual verification steps defined in `plan.md`.
- Verify:
  - Latency is acceptable.
  - Tenant isolation is strictly enforced (try to access Business A data from Phone B).
  - Undo works reliability.
- update `walkthrough.md` with results.

## Definition of Done

- [ ] "Schedule" command works for clear cases.
- [ ] Ambiguous input saves as a Request.
- [ ] Walkthrough artifact created/updated.
- [ ] Feature is ready for merge.
