---
work_package_id: WP02
title: Wage Calculation Logic
lane: planned
dependencies: []
subtasks: [T006, T007, T008, T009]
---

# Work Package: Wage Calculation Logic

## Inspection

- **Goal**: Implement the business logic for calculating wages. This is "Pure Logic" work, independent of the database or HTTP layers.
- **Role**: Backend Engineer / Algorithm Developer.
- **Outcome**: A robust `WageCalculator` service that can handle all 4 specified wage models correctly.

## Context

We need a flexible system to calculate how much an employee earns for a specific activity. Because we have multiple models (Commission, Hourly Job, Hourly Shift, Fixed Daily), we'll use the **Strategy Pattern**.

This code fits in `src/services/wages/`.

## Detailed Subtasks

### T006: Define WageStrategy Interface

**Goal**: Create the protocol/abstract base class.
**Files**: `src/services/wages/strategy.py`
**Interface**:

- `calculate(config: WageConfiguration, context: dict) -> float`
- `context` dictionary will contain keys like `job_revenue`, `start_time`, `end_time`, `is_check_in`.

### T007: Implement Concrete Strategies

**Goal**: Implement the logic for each wage type.
**Files**: `src/services/wages/strategies.py`
**Strategies**:

1. **CommissionStrategy**: `amount = context['job_revenue'] * (config.rate_value / 100)`
2. **HourlyJobStrategy**: `duration_hours = (context['end_time'] - context['start_time']).total_seconds() / 3600`; `amount = duration_hours * config.rate_value`
3. **HourlyShiftStrategy**: Similar to Job, but checks `context['shift_start']` and `context['shift_end']`.
4. **FixedDailyStrategy**: `amount = config.rate_value` (Fixed sum per day/check-in).

**Edge Cases**:

- Duration should be rounded to 2 decimal places (or whatever business logic dictates - usually nearest 15 mins, but spec implies exact math. Stick to exact float math for now, rounded at payment).
- Handle zero duration gracefully.

### T008: Implement WageCalculator Service

**Goal**: Create a factory/facade to use the strategies easily.
**Files**: `src/services/wages/calculator.py`
**Functionality**:

- Class `WageCalculator`
- Method `calculate_wage(config: WageConfiguration, context: WageContext) -> float`
- It should dispatch to the correct strategy based on `config.model_type`.

### T009: Unit Tests

**Goal**: Verify the math is correct.
**Files**: `tests/unit/test_wage_calculator.py`
**Scenarios**:

- **Commission**: Job $500, Rate 20% -> $100.
- **Hourly**: 1.5 hours work, $20/hr -> $30.
- **Hourly**: Check 15 min duration.
- **Fixed**: $150/day -> $150.
- **Validation**: Ensure missing context keys raise appropriate errors (e.g., Hourly strategy missing 'start_time').

## Testing

- Run `pytest tests/unit/test_wage_calculator.py`.
- Ensure 100% coverage of branching logic in strategies.

## Definition of Done

- All strategies implemented.
- Calculator service routes correctly.
- Tests pass.
