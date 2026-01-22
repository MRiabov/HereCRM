# Research: Expenses & Payroll Ledger

## Decision: Ledger Architecture

**Choice**: Simple Transaction Log (Append-Only)
**Rationale**:

- Fits the requirement for "Balance Owed" without full double-entry complexity.
- "Payouts" are simply negative entries.
- Easy to aggregate via `SUM(amount)` per employee.
- SQLite friendly.
**Alternatives Considered**:
- Full Double Entry Options (Asset/Liability/Equity tables): Too complex for this MVP.
- "Current Balance" Column on Employee: Rejected because it lacks audit history (recalculating from log is safer).

## Decision: Wage Logic

**Choice**: Strategy Pattern (`WageStrategy` interface)
**Rationale**:

- Employees can have very different pay models.
- Allows isolated testing of "Commission Logic" vs "Hourly Logic".
**Alternatives Considered**:
- Hardcoded `if/elif` in `JobService`: Rejected because it would become a maintenance nightmare as new models (e.g., "Overtime") are added.

## Decision: Command Parsing

**Choice**: Existing LLM Tool calling + Standard parsing
**Rationale**:

- Consistent with user Constitution (LLM-First).
- `start job #123` can be parsed by an LLM tool `StartJob(job_id=123)`.
