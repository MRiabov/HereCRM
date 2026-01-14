---
work_package_id: WP02
slug: automatic-progression
lane: planned
subtasks: [T005, T006, T007, T008]
history:
  - date: 2026-01-14
    event: Created work package prompt.
---

# WP02: Automatic State Progression

## Objective

Implement the logic that automatically transitions customers between pipeline stages based on system events.

## Context

This work leverages the `EventBus` from WP01. When a job is created, the system should catch this event and update the owner's stage accordingly.

## Subtasks

### T005: Create Pipeline Handlers

- **File**: `src/services/pipeline_handlers.py`
- **Action**: Create a new service file for stage transition logic.
- **Responsibility**: Define functions that respond to `JOB_CREATED` and communication events.

### T006: Signal Job Creation

- **File**: `src/services/crm_service.py` (or relevant service)
- **Action**: Emit a `JOB_CREATED` event on the `EventBus` when a new job is successfully added.
- **Payload**: Include at least `customer_id`.

### T007: Implement Stage Update Logic

- **File**: `src/services/pipeline_handlers.py`
- **Logic**:
  - Catch `JOB_CREATED`.
  - Fetch customer job count.
  - If count == 1: Set stage to `CONVERTED_ONCE`.
  - If count > 1: Set stage to `CONVERTED_RECURRENT`.
  - Ensure manual stages like `NOT_INTERESTED` or `LOST` are overridden by new sales activity unless specifically forbidden (Spec 002 says yes).

### T008: Contacted Trigger

- **Action**: Implement a way to detect the first interaction with a customer (incoming or outgoing message) and set stage to `CONTACTED` if it was `NOT_CONTACTED`.

## Definition of Done

- Creating a customer results in `NOT_CONTACTED`.
- Adding the first job moves them to `CONVERTED_ONCE`.
- Adding the second job moves them to `CONVERTED_RECURRENT`.
- Logic is decoupled via `EventBus`.
