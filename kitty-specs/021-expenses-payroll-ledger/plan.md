# Implementation Plan: Expenses & Payroll Ledger

*Path: [templates/plan-template.md](templates/plan-template.md)*

**Branch**: `021-expenses-payroll-ledger` | **Date**: 2026-01-22 | **Spec**: [Spec](spec.md)
**Input**: Feature specification from `/kitty-specs/021-expenses-payroll-ledger/spec.md`

## Summary

Implement a financial tracking system for expenses and employee payroll within the existing CRM. This includes a flexible expense recording system (linked to jobs or general) and a payroll ledger that accumulates wages based on configurable models (Commission, Hourly, Daily). The system will use a simple transaction log approach (credit/debit) stored in SQLite to track "Balance Owed" to employees, accessible via chat commands.
API Exposure: Finance endpoints (List Expenses, Get Ledger) for PWA.
API Exposure: Finance endpoints (List Expenses, Get Ledger) for PWA.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastAPI, SQLAlchemy (Sync/Async), Pydantic
**Storage**: SQLite (sharing existing project database)
**Testing**: pytest
**Target Platform**: Linux server
**Project Type**: Single project (Modular Monolith)

**Core Technical Decisions**:

- **Ledger Strategy**: Use a single `ledger_entries` table acting as a transaction log. Positive values = Earned Wage, Negative values = Payouts. Summing them gives the current balance.
- **Wage Calculation**: Implement a `WageCalculator` service using the Strategy Pattern to handle different wage models (`COMMISSION_PERCENT`, `HOURLY_PER_JOB`, `HOURLY_PER_SHIFT`, `FIXED_DAILY`) without complex `if/else` chains.
- **Expense Linking**: `Expense` entity will have nullable Foreign Keys to `Job` and `LineItem` to allow flexible cost allocation.
- **Command Parsing**: Extend the existing `MessagingService` and Tool definitions to parse `check in`, `start job #123`, and `add expense` commands.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **LLM-First Text Processing**: The feature relies on natural language commands ("Add expense office supplies $50") which will be parsed by the LLM into structured tool calls.
- [x] **Intent Transparency**: Wage accumulations and expense recordings will trigger confirmation messages to the user (e.g., "Shift started at 08:00").
- [x] **Progressive Documentation**: We will update `messages.yaml` with help text for the new financial commands.

## Project Structure

### Documentation (this feature)

```
kitty-specs/021-expenses-payroll-ledger/
├── plan.md              # This file
├── research.md          # Ph 0
├── data-model.md        # Ph 1
├── contracts/           # Ph 1
└── tasks.md             # Ph 2
```

### Source Code (repository root)

```
src/
├── models/              # New Expense, LedgerEntry, WageConfiguration models
├── services/            # WageCalculator, LedgerService
├── tools/               # AddExpenseTool, CheckInTool, PayoutTool
└── assets/              # messages.yaml updates

tests/
├── unit/                # logic tests for WageCalculator
└── integration/         # workflow tests for LedgerService
```

**Structure Decision**: Standard single project structure leveraging existing folders.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Strategy Pattern for Wages | High variability in wage logic (Hourly vs Commission) | Hardcoded `if/else` scales poorly as new wage types are added. |
