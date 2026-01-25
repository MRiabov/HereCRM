---
work_package_id: WP04
title: Ledger & Payouts
lane: "done"
dependencies: []
subtasks: [T015, T016, T017, T018, T019]
review_status: "has_feedback"
reviewed_by: "MRiabov"
agent: "Antigravity"
shell_pid: "587193"
---

# Work Package: Ledger & Payouts

## Inspection

- **Goal**: The "Money" phase. Connect the Time Tracking events to the Wage Calculator and store the results in the Ledger. Also implement Payouts.
- **Role**: Backend Engineer / Integration.
- **Outcome**: Completed shifts/jobs generate money in the employee's ledger.

## Context

This is the integration point.

- When `check_out` happens (WP03), we need to:
    1. Look up User's `WageConfiguration`.
    2. Call `WageCalculator.calculate`.
    3. Create a `LedgerEntry` (Credit).
- When `finish_job` happens, similar flow.

## Detailed Subtasks

### T015: Implement LedgerService

**Goal**: Manage the `ledger_entries` table.
**Files**: `src/services/ledger.py`
**Methods**:

- `add_entry(employee_id, amount, type, description, job_id=None)`: Creates record.
- `get_balance(employee_id) -> float`: Sum of all `amount` for user.
- `get_history(employee_id, limit=50)`: Returns recent entries.

### T016: Wiring Time Tracking to Wages

**Goal**: Modify `TimeTrackingService` (or create a higher-level `PayrollOrchestrator`) to trigger ledger writes.
**Files**: `src/services/time_tracking.py` (Modify) OR `src/services/payroll.py` (New wrapper)
**Logic**:

- In `finish_job`:
  - Fetch User's WageConfig.
  - If model is `HOURLY_PER_JOB` or `COMMISSION`:
    - Calculate wage (need Job Revenue for commission).
    - Call `LedgerService.add_entry(amount, type=WAGE, ...)`.
- In `check_out`:
  - Fetch User's WageConfig.
  - If model is `HOURLY_PER_SHIFT` or `FIXED_DAILY`:
    - Calculate wage.
    - Call `LedgerService.add_entry`.

**Design Note**: Ensure we don't crash if configuration is missing (log warning/error, but maybe don't fail the user operation? Or fail clearly telling them to set config).

### T017: Payout Tool

**Goal**: Tool for business owner to pay employees.
**Files**: `src/tools/financial.py`
**Tool**: `RecordPayoutTool(employee_id, amount, note)`
**Action**:

- Call `LedgerService.add_entry(amount=-amount, type=PAYOUT, ...)` (Make sure to negate the amount for debit!).
- Return "Recorded payout of $X. New Balance: $Y".

### T018: Get Balance Tool

**Goal**: Tool for employees/owners to check money owed.
**Files**: `src/tools/financial.py`
**Tool**: `GetBalanceTool(employee_id)` (Defaults to current user if employee).
**Action**:

- Call `LedgerService.get_balance`.
- Return "Current Balance Owed: $X".

### T019: End-to-End Tests

**Goal**: Verify the whole chain works.
**Files**: `tests/integration/test_ledger_flow.py`
**Scenarios**:

1. **Hourly Job Flow**:
    - Configure User ($20/hr, Job based).
    - Start Job -> Wait 1 sec (mock time to 1 hour) -> Finish Job.
    - Verify Ledger has +$20 entry.
    - Verify Balance is $20.
2. **Payout Flow**:
    - User has $20 balance.
    - Call PayoutTool($20).
    - Verify Ledger has -20 entry.
    - Verify Balance is $0.
3. **Commission Flow**:
    - Configure User (10% Commission).
    - Finish Job (Revenue $500).
    - Verify Ledger has +$50 entry.

## Testing

- `pytest tests/integration/test_ledger_flow.py`

## Definition of Done

- "Working for money" works.
- Payouts work.
- Balances are accurate.

## Activity Log

- 2026-01-22T12:25:15Z – unknown – lane=planned – Moved to planned
- 2026-01-22T17:56:14Z – Antigravity – shell_pid=284006 – lane=doing – Started implementation via workflow command
- 2026-01-22T18:18:26Z – Antigravity – shell_pid=284006 – lane=for_review – Ready for review: Ledger implemented, time tracking wired to wages, payout and balance tools added.
- 2026-01-25T08:12:49Z – Antigravity – shell_pid=284006 – lane=for_review – Implemented LedgerService, integrated with TimeTracking, and added financial tools. All tests passed.
- 2026-01-25T08:14:44Z – Antigravity – shell_pid=587193 – lane=doing – Started review via workflow command
- 2026-01-25T08:16:10Z – Antigravity – shell_pid=587193 – lane=done – Review passed: Implementation is solid and integration tests pass.
