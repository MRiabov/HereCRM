---
work_package_id: WP05
title: Expense Management
lane: planned
dependencies: []
subtasks: [T020, T021, T022, T023]
---

# Work Package: Expense Management

## Inspection

- **Goal**: Implement the ability to record expenses. Independent of wages, but sharing the same domain.
- **Role**: Backend Engineer.
- **Outcome**: Users can add expenses via chat.

## Context

Simple CRUD for the `Expense` entity, but exposed via an LLM Tool.

## Detailed Subtasks

### T020: Implement ExpenseService

**Goal**: CRUD Logic.
**Files**: `src/services/expenses.py`
**Methods**:

- `create_expense(amount, description, category, job_id=None, ...)` -> Expense
- `get_expenses(filters...)` -> List[Expense]

### T021: AddExpenseTool

**Goal**: The main interaction point for User Story 1 & 2.
**Files**: `src/tools/expenses.py`
**Tool**: `AddExpenseTool`
**Arguments**:

- `amount` (float)
- `description` (string)
- `category` (string, default "General")
- `job_id` (int, optional)
**Action**:
- Call `ExpenseService.create_expense`.
- Return "Recorded expense: [Desc] $X (Linked to Job #Y if applicable)".

### T022: Reporting Query

**Goal**: Support simple listing for now (detailed reporting in WP06).
**Files**: `src/services/expenses.py`
**Method**:

- Ensure `get_expenses` allows filtering by `job_id` or `date_range`.

### T023: Tests

**Goal**: Verify expense creation.
**Files**: `tests/integration/test_expenses.py`
**Scenarios**:

- Create general expense.
- Create expense linked to Job #1.
- List expenses for Job #1.

## Definition of Done

- `AddExpenseTool` works.
- Expenses are saved to DB.
