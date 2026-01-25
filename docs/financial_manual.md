# Financial Tools Manual

HereCRM includes powerful tools for managing expenses, payroll, and job profitability.

## Expenses

Track job-related or general business expenses directly from WhatsApp.

**Commands:**

- `Add expense [amount] [description]`
  - Example: "Add expense 50 for fuel"
  - Example: "Add expense 120.50 for materials"

Expenses are verified against the active job if you are currently handling one, or recorded as general business expenses.

## Time Tracking & Payroll

Manage employee hours and payments.

**For Employees:**

- `Check in`: Start tracking time.
- `Start job #[id]`: Link time to a specific job.
- `Check out`: Stop tracking time.
- `Check balance`: See current outstanding wages.

**For Business Owners:**

- `Record payout [amount]`: Record a payment to an employee (clears their balance).
  - Note: This is a record-keeping action; actual money transfer must be done separately.
- `Export ledger`: Download a report of all time entries and payouts.

## Reporting & Exports

Get data out of HereCRM for your accountant.

**Commands:**

- `Export expenses to [csv/excel]`
- `Export payroll to [csv/excel]`
- `Export jobs to [csv/excel]`

Reports are generated and a secure download link is sent to you.

## Job Profitability

When viewing a completed job, you can see a breakdown of profitability:

- **Revenue**: Total invoiced amount.
- **Costs**: Expenses + Labor (time spent * employee rate).
- **Net Profit**: Revenue - Costs.
