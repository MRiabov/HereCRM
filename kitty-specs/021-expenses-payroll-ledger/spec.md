# Feature Specification: Expenses & Payroll Ledger

**Feature Branch**: `021-expenses-payroll-ledger`
**Created**: 2026-01-22
**Status**: Draft
**Input**: Integrated request for expense tracking, job costing, and employee payroll ledger with variable wage models (commission, hourly, daily).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manual Expense Tracking (Priority: P1)

As a Business Owner, I want to record general business expenses (e.g., "Truck repair $200") so that I can track my operational costs independent of specific jobs.

**Why this priority**: Basic expense tracking is the foundation of the system.

**Independent Test**: submitting a text command or form "Add expense - equipment 500$" and verifying it appears in the expense list with the correct amount and category.

**Acceptance Scenarios**:

1. **Given** a business owner is logged in, **When** they input "Add expense: Office Supplies $50", **Then** a new Expense record is created for $50 labeled "Office Supplies".
2. **Given** an existing expense, **When** the owner views the expense report, **Then** the item is listed with date, amount, and description.

---

### User Story 2 - Job-Linked Cost Allocation (Priority: P1)

As a Business Owner, I want to attach expenses to specific jobs or line items (e.g., "Tiles cost $50") so that I can calculate the true profit of a job.

**Why this priority**: Essential for accurate "Per Job" profit reporting.

**Independent Test**: Create a job with $200 revenue, add a linked expense of $50, and verify the job's "Gross Profit" report shows $150.

**Acceptance Scenarios**:

1. **Given** a job worth $500, **When** I add an expense "Materials $100" linked to this job, **Then** the expense is recorded and the Job Profitability view shows $400 net.
2. **Given** a job with a "Window Cleaning" line item, **When** I set a rule "Expense is 30% of Window Cleaning", **Then** the system automatically creates a cost entry calculated from that line item's revenue.

---

### User Story 3 - Employee Wage Calculation (Priority: P1)

As a Business Owner, I want employee wages to be calculated automatically based on their assigned model (Commission, Hourly, or Daily) so that I don't have to do manual math.

**Why this priority**: Reduces administrative burden and errors in payroll.

**Independent Test**: Configure an employee as "Hourly", have them "Check In" and "Check Out" via chat, and verify their Ledger Balance increases by (Hours * Rate).

**Acceptance Scenarios**:

1. **Given** Employee A is on "30% Commission", **When** they complete a $200 job, **Then** $60 is added to their "Balance Owed" ledger.
2. **Given** Employee B is "Hourly per Job", **When** they "Start Job" at 10:00 and "Finish Job" at 11:00 ($20/hr), **Then** $20 is added to their ledger.
3. **Given** an enabled "Tax Set Aside" of 20%, **When** a $100 wage is generated, **Then** the system shows "$80 Net Pay / $20 Tax Hold" in the owner's view (informational only).

---

### User Story 4 - Payroll Ledger & Payouts (Priority: P1)

As a Business Owner, I want to view what I owe each employee and record payouts so I can manage cash flow and clear balances.

**Why this priority**: Completes the cycle from "Earning" to "Paying".

**Independent Test**: View a balance of $500 for an employee, record a "Cash Payout" of $500, and verify the ending balance is $0.

**Acceptance Scenarios**:

1. **Given** an employee has a balance of $1000, **When** I record a payout of $1000, **Then** the balance updates to $0 and a Payout record is created.
2. **Given** multiple unpaid wages, **When** I view the "Payroll Dashboard", **Then** I see a total "Outstanding Payroll" figure.

---

### User Story 5 - Enhanced Employee Workflow (Priority: P2)

As a Field Employee, I want to "Check In" and "Start Job" via text commands so that my time and wages are tracked accurately.

**Why this priority**: Enabler for the Hourly/Daily wage models defined in User Story 3.

**Independent Test**: Send "start job #123" from an employee account and verify the Job status updates to 'In Progress' with a timestamp.

**Acceptance Scenarios**:

1. **Given** I am an employee, **When** I send "Check In", **Then** my "Shift Start" time is recorded.
2. **Given** I am at a job site, **When** I send "Start #123", **Then** the job start time is recorded.

---

### Edge Cases

- **Missed Clocks**: If an employee forgets to "Check In" or "Start Job", the Business Owner must be able to manually insert or edit the time entry to correct the accumulated wage.
- **Rate Changes**: Changing an Employee's wage rate (e.g., from $20/hr to $25/hr) MUST only affect future calculations, preserving the historical ledger values.
- **Negative Balance**: The system should allow "Advance Payments" (Payout > Balance) resulting in a negative balance, which future wages will offset.
- **Deleted Jobs**: If a Job is deleted, linked Expenses should be preserved (orphaned or unlinked) rather than deleted, to maintain financial records.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow creation of `Expense` records with: Amount, Description, Date, Vendor (optional), and Link (Job, LineItem, or General).
- **FR-002**: The `Employee` entity MUST support configuration of a `WageModel`:
  - `COMMISSION_PERCENT` (Apply % to Job Revenue)
  - `HOURLY_PER_JOB` (Paid for time strictly between Start/Finish Job)
  - `HOURLY_PER_SHIFT` (Paid for time between Check-In/Check-Out)
  - `FIXED_DAILY` (Flat rate per day with check-in)
- **FR-003**: The Employee Workflow (Spec 016) MUST accept new commands:
  - `check in` / `start day`: Records shift start.
  - `check out` / `end day`: Records shift end.
  - `start #[ID]`: Records job start timestamp.
- **FR-004**: Completing a job (or shift) MUST trigger a `LedgerEntry` creation that credits the employee's balance based on their `WageModel`.
- **FR-005**: If "Tax Set Aside" is configured, the system MUST calculate and display the estimated tax portion of any wage entry, but DOES NOT deduct it from the ledger (it is informational for the owner).
- **FR-006**: The system MUST support a `Record Payout` action (Manual) that creates a debit `LedgerEntry`, reducing the employee's specific balance.
- **FR-007**: Expenses and Ledger entries MUST be exportable via the existing CSV export framework (Spec 007).
- **FR-008**: Job Profitability calculations MUST deduct linked Expenses and linked Wage Costs from Revenue to show "Net Job Profit".

### Key Entities

- **Expense**: Records a cost. Can be linked to a Job (reducing job profit) or unlinked (operational overhead).
- **LedgerEntry**: A credit (wage earned) or debit (payout) transaction for an Employee.
- **WageConfiguration**: Stores the model (Hourly/Commission) and Rate for an employee.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: "Net Job Profit" is correctly calculated (Revenue - Expenses - Wages) for 100% of jobs with linked costs.
- **SC-002**: Employee "Balance Owed" is accurate within $0.01 based on configured wage rules and logged times.
- **SC-003**: Employee commands `check in` and `start #[ID]` are recognized and timestamped within 2 seconds.
- **SC-004**: Manual Payouts immediately reflect in the employee's running balance.
