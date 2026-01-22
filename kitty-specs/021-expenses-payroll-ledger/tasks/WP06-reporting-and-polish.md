---
work_package_id: WP06
title: Reporting & Polish
lane: planned
dependencies: []
subtasks: [T024, T025, T026, T027]
---

# Work Package: Reporting & Polish

## Inspection

- **Goal**: Tie it all together with reports and documentation.
- **Role**: Full Stack / Product Engineer.
- **Outcome**: The feature is usable and measurable.

## Context

We have the data (Expenses, Ledger). Now we need to expose it nicely.

## Detailed Subtasks

### T024: Job Profitability Logic

**Goal**: Calculate "Net Job Profit".
**Files**: `src/services/jobs.py` (or reporting service)
**Logic**:

- `Revenue` = Sum of Line Items.
- `Cost_Expenses` = Sum of linked Expenses.
- `Cost_Labor` = Sum of linked LedgerEntries (Wage type, related_job_id).
- `Net Profit` = Revenue - Cost_Expenses - Cost_Labor.
- Add this to the "Get Job details" output or a specific "Profit Report".

### T025: CSV Export

**Goal**: Export data for accounting.
**Files**: `src/services/export.py`
**Actions**:

- Register `Expenses` and `LedgerEntries` with the CSV exporter (Feature 007).
  - Columns for Expenses: Date, Amount, Category, Desc, JobID.
  - Columns for Ledger: Date, Employee, Amount, Type, Desc.

### T026: Update Messages & Prompts

**Goal**: Make the AI aware of the new capabilities.
**Files**: `src/assets/messages.yaml` or `src/prompts/system.md`
**Changes**:

- Add help sections for "Financials":
  - "Add expense [amount] [desc]..."
  - "Time tracking: Check in, Start job #..."
  - "Payroll: Check balance, Record payout..."

### T027: Documentation

**Goal**: User Manual.
**Files**: `docs/manual.md`
**Content**:

- "How to set up employee items" (Setting WageConfig).
- "How to track time".
- "How to run payroll".

## Testing

- **Manual Verification**: Run through the full user stories from the Spec.

## Definition of Done

- Feature is documented.
- AI knows how to use it.
- Exports work.
