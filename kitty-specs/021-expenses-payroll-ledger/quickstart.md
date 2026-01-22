# Quickstart

## Setup & Testing the Flow

### 1. Configure Employee Wage

As an Admin, you must first configure the wage model for an employee. (Currently via DB or future UI, for MVP use SQL/Shell).

```python
# Example setup in shell
wage_config = WageConfiguration(employee_id=emp.id, model_type='HOURLY_PER_JOB', rate_value=20.0)
session.add(wage_config)
session.commit()
```

### 2. Employee Workflow (Hourly Per Job)

1. **Employee sends**: "Start job #100"
   - System records `start_time` for the job/employee link.
   - Reply: "Job #100 started at 10:00."
2. **Wait**: Simulate time passing (e.g. 1 hour).
3. **Employee sends**: "Finish job #100" or "Job #100 done"
   - System calculates duration (1 hr) * rate ($20).
   - System creates `LedgerEntry(amount=20.0, entry_type='WAGE')`.
   - Reply: "Job finished. Earned $20.00."

### 3. Expense Workflow

1. **Owner sends**: "Add expense: Tiles $50 for job #100"
   - System extracts amount ($50) and job (#100).
   - JSON Tool Call: `AddExpense(amount=50, description="Tiles", job_id=100)`
   - System creates `Expense` record linked to Job #100.
   - Reply: "Added expense $50 for Job #100."

### 4. Payout Workflow

1. **Owner sends**: "Pay John $500"
   - System checks John's balance.
   - System creates `LedgerEntry(amount=-500.0, entry_type='PAYOUT')`.
   - Reply: "Recorded payout of $500 to John. Remaining balance: $X."
