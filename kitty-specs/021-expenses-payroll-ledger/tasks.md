# Work Packages: Expenses & Payroll Ledger

**Feature**: 021-expenses-payroll-ledger
**Status**: Planned

## 1. Foundation & Data Model (WP01)

**Goal**: Create the database schema and SQLAlchemy models for Expenses, Ledger, and Wage Configuration.
**Priority**: Critical path
**Tests**: `tests/unit/test_models_021.py` verify schema and relationships.

- [x] T001: Create migration for `WageModel` enum, `Expense`, `LedgerEntry`, `WageConfiguration` tables.
- [x] T002: Create SQLAlchemy models in `src/models/` matching the schema.
- [x] T003: Update `User` model with `wage_config` relationship and `current_shift_start` (datetime) field.
- [x] T004: Update `Job` model with `expenses` relationship and `started_at` (datetime) field.
- [x] T005: Create factory seed data to verify relationships can be populated.

**Implementation**:

- Use Alembic for migrations.
- Extend existing `User` and `Job` models.
- Ensure `WageModel` is an Enum.

**Dependencies**: None
**Risks**: Migration conflicts if other features modified User/Job recently.

## 2. Wage Calculation Logic (WP02)

**Goal**: Implement the core business logic for calculating wages based on different strategies.
**Priority**: High
**Tests**: `tests/unit/test_wage_calculator.py` coverage for all strategies.

- [x] T006: Define `WageStrategy` abstract base class.
- [x] T007: Implement `CommissionStrategy`, `HourlyJobStrategy`, `HourlyShiftStrategy`, `FixedDailyStrategy`.
- [x] T008: Implement `WageCalculator` service that accepts a strategy and context (time/job) to return amount.
- [x] T009: Write comprehensive unit tests for all mathematical scenarios (rounding, zero time, etc.).

**Implementation**:

- Pure Python logic, easy to test in isolation.
- Use Strategy Pattern as planned.

**Dependencies**: WP01 (Models - for Enum types)
**Risks**: Precision errors (use Decimal/Float carefully).

## 3. Employee Time Tracking (WP03)

**Goal**: Implement the state management for employee shifts and job timers using Tools.
**Priority**: High
**Tests**: `tests/integration/test_time_tracking.py` verifying state transitions.

- [x] **T010**: Implement `TimeTrackingService` methods: `start_shift`, `end_shift`, `start_job`, `finish_job`.
- [x] **T011**: Implement `CheckInTool` and `CheckOutTool` connecting to the service.
- [x] **T012**: Implement `JobStartTool` and `JobFinishTool`.
- [x] **T013**: Handle state persistence (updating `current_shift_start` on User, `started_at` on Job).
- [x] **T014**: Integration tests ensuring valid state transitions (can't start job if not checked in, etc. - optionally).

**Implementation**:

- "Check In" -> Updates User.current_shift_start.
- "Check Out" -> Will trigger wage calc (next WP), currently just validates state.
- "Start Job" -> Updates Job.started_at.

**Dependencies**: WP01
**Risks**: Handling forgot-to-clock-out scenarios (out of scope for MVP, but keep in mind).

## 4. Ledger & Payouts (WP04)

**Goal**: Connect time tracking to the ledger and allow payouts.
**Priority**: High
**Tests**: `tests/integration/test_ledger_flow.py` full cycle test.

- [x] T015: Implement `LedgerService` with `add_entry` (credit/debit), `get_balance`.
- [x] T016: Wire `TimeTrackingService` to call `WageCalculator` then `LedgerService` on "Finish Job" and "Check Out".
- [x] T017: Implement `PayoutTool` (Create debit entry).
- [x] T018: Implement `GetBalanceTool` (Read balance).
- [x] T019: End-to-end tests: Check In -> Wait -> Check Out -> Verify Ledger Balance -> Payout -> Verify Zero.

**Implementation**:

- This is the integration glue.
- Modify `TimeTrackingService` from WP03 to perform the calculation and ledger write.

**Dependencies**: WP02 (Logic), WP03 (Time Tracking), WP01 (Models)
**Risks**: Double counting if events fire twice (ensure idempotency or transactional safety).

## 5. Expense Management (WP05)

**Goal**: Allow adding expenses linked to jobs or general categories.
**Priority**: Medium
**Tests**: `tests/integration/test_expenses.py`.

- [ ] **T020**: Implement `ExpenseService` with `create_expense`, `list_expenses`.
- [ ] **T021**: Implement `AddExpenseTool` with arguments for `amount`, `description`, `job_id` (optional).
- [ ] **T022**: Implement expense listing functionality (for reporting).
- [ ] **T023**: Integration tests for creating expenses and linking to jobs.

**Implementation**:

- Independent module, can be built anytime after WP01.

**Dependencies**: WP01
**Risks**: None specific.

## 6. Reporting & Polish (WP06)

**Goal**: Finalize reports, CSV exports, and documentation/prompts.
**Priority**: Low
**Tests**: `tests/unit/test_profit_calc.py`.

- [ ] **T024**: Implement `JobService.calculate_profit(job_id)` -> Revenue - Expenses - Wages.
- [ ] **T025**: Implement/Update CSV export to include Expenses and Ledger tables.
- [ ] **T026**: Update `messages.yaml` with help text for new commands.
- [ ] **T027**: Update `manual.md` with "Financial Features" section.

**Implementation**:

- Polish phase.

**Dependencies**: WP04, WP05 (Data must exist to report on it)
