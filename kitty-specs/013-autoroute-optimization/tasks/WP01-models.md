---
work_package_id: "WP01"
title: "Database Migrations & Models"
lane: "doing"
dependencies: []
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
agent: "antigravity"
shell_pid: "3980068"
---

# Work Package 01: Database Migrations & Models

## Objective

Establish the foundational data models required for storing customer availability and routing optimization parameters (locations, durations).

## Context

We are implementing an "autoroute" feature to optimize job scheduling. This requires new data points:

- Customers need to define when they are available.
- Employees (Users) need a starting location for the routing algorithm.
- Jobs and Services need duration estimates for time calculations.

## Subtasks

### T001: Create `CustomerAvailability` model and migration

**Purpose**: Store specific time windows when a customer is available.
**Files**: `src/models.py`, `migrations/`
**Steps**:

1. Define `CustomerAvailability` in `src/models.py`:
    - `id`: Integer, PK.
    - `customer_id`: ForeignKey to `customers.id`.
    - `start_time`: DateTime (UTC), non-nullable.
    - `end_time`: DateTime (UTC), non-nullable.
    - `is_available`: Boolean, default True.
    - Relationship: `Customer` should have `availability` relationship (lazy='dynamic' or list).
2. Generate migration: `alembic revision --autogenerate -m "add_customer_availability"`.
3. Verify migration script correctness.

### T002: Update `User` model with start location fields

**Purpose**: Store the default starting coordinates for employees.
**Files**: `src/models.py`, `migrations/`
**Steps**:

1. Add fields to `User` in `src/models.py`:
    - `default_start_location_lat`: Float, nullable.
    - `default_start_location_lng`: Float, nullable.
2. Generate migration (can be combined with T001 or separate).

### T003: Update `Job` and `Service` with duration fields

**Purpose**: Store duration estimates for routing calculations.
**Files**: `src/models.py`, `migrations/`
**Steps**:

1. Add fields to `Service` (template) and `Job` (instance):
    - `estimated_duration`: Integer (minutes), default 60 (or appropriate default).
2. Generate migration.

### T004: Implement `AvailabilityService` basics

**Purpose**: specific logic for managing availability (adding windows, checking overlap).
**Files**: `src/services/availability_service.py`
**Steps**:

1. Create `AvailabilityService` class.
2. Method: `add_availability(customer_id, start_time, end_time)`.
    - Validate `start_time < end_time`.
3. Method: `get_availability(customer_id, date_range)`.
4. Method: `is_customer_available(customer_id, time_slot)` (helper for later).

## Test Strategy

- **Unit Tests**:
  - Test model instantiation.
  - Test `AvailabilityService` CRUD operations.
  - Test validation logic (start < end).
- **Integration Tests**:
  - Test DB persistence of availability.
  - Test adding start location to a User.

## Definition of Done

- [ ] Models defined in `src/models.py`
- [ ] Migrations created and applied successfully
- [ ] `AvailabilityService` implemented with basic CRUD
- [ ] Unit tests passing

## Activity Log

- 2026-01-21T09:32:20Z – antigravity – shell_pid=3980068 – lane=doing – Started implementation via workflow command
