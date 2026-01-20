---
work_package_id: WP02
title: Intelligent Assignment Logic
lane: "doing"
dependencies: []
subtasks: [T005, T006, T007]
agent: "Antigravity"
shell_pid: "3837732"
---

# Work Package 02: Intelligent Assignment Logic

## Objective

Enhance the assignment service with "human" capabilities: resolving names vaguely (e.g., "John" -> "John Smith") and checking for business logic constraints (conflicts, valid roles).

## Files

- `src/services/assignment_service.py` (Modify)
- `tests/unit/test_assignment_logic.py` (New)

## Detailed Guidance

### T005: Fuzzy Name Matching

**Purpose**: interpret user commands like "Assign to Bob" without needing IDs.

1. Add a method `find_employee_by_name(business_id: int, name_fragment: str) -> List[User]`.
2. Logic:
   - Specific case-insensitive match (SQL `ILIKE`).
   - If no exact match, potentially use fuzzy matching (check if `thefuzz` is needed, or just strict prefix matching for now).
   - Return a list of candidates.
3. This will be used by the Tool layer later to disambiguate.

### T006: Enhanced Assign Job Logic

**Purpose**: Update `assign_job` to be safer.

1. Modify `assign_job` (or rename to `execute_assignment`) to accept `job_id` and `employee_id`.
2. **Validation 1**: Ensure `employee_id` belongs to the same business.
3. **Validation 2**: Ensure (softly) no overlap. Check if employee has another job at `job.scheduled_at`.
   - If conflict, log a warning or return a structure indicating specific warning (e.g., `AssignmentResult(success=True, warning="Double booked")`).
4. **Validation 3**: Verify job exists.

### T007: Robust Unit Tests

**Purpose**: Verify the logic handles messiness.

1. Create `tests/unit/test_assignment_logic.py`.
2. Test Case: "Assign to John" where "John Doe" and "Johnny" exist.
3. Test Case: Assigning a job to a user in a different business (Security check).
4. Test Case: Assigning a job that creates a time conflict (Verify warning).

## Acceptance Criteria

- `find_employee_by_name` accurately retrieves users.
- `assign_job` prevents cross-business data leaks.
- Conflict detection logic works.

## Implementation Command

`spec-kitty implement WP02 --base WP01`

## Activity Log

- 2026-01-20T16:52:47Z – Antigravity – shell_pid=3837732 – lane=doing – Started implementation via workflow command
