---
work_package_id: WP01
slug: foundational-infrastructure
lane: "doing"
subtasks: [T001, T002, T003, T004]
agent: "codex"
history:
  - date: 2026-01-14
    event: Created work package prompt.
---

# WP01: Foundational Pipeline Infrastructure

## Objective

Set up the core data structures and communication patterns required for the pipeline progression feature.

## Context

We need to track customer stages (`Not Contacted`, `Contacted`, `Converted Once`, etc.) and provide a decoupled way to trigger stage updates based on external events like job creation.

## Subtasks

### T001: Define `PipelineStage` Enum

- **File**: `src/models.py`
- **Action**: Create a `PipelineStage` Enum inheriting from `str` and `Enum`.
- **Values**: `NOT_CONTACTED`, `CONTACTED`, `CONVERTED_ONCE`, `CONVERTED_RECURRENT`, `NOT_INTERESTED`, `LOST`.

### T002: Update `Customer` Model

- **File**: `src/models.py`
- **Action**: Add `pipeline_stage: PipelineStage` field to the `Customer` class.
- **Default**: `PipelineStage.NOT_CONTACTED`.
- **Note**: Ensure Pydantic/dataclass compatibility with existing serialization.

### T003: Implement `EventBus`

- **File**: `src/events.py`
- **Action**: Implement a simple `EventBus` that allows subscribing to events and emitting them.
- **Requirement**: Support for named events (e.g., `JOB_CREATED`) and associated data (e.g., `customer_id`).

### T004: Initialize and Setup

- **File**: `src/main.py`
- **Action**: Initialize the `EventBus` instance and ensure it's accessible (e.g., via app state or a global singleton if that's the project pattern).

## Definition of Done

- `PipelineStage` enum is defined and used in `Customer`.
- `EventBus` is implemented and can successfully manage subscribers.
- Existing tests pass with the new model field (might need default values in mocks).

## Activity Log

- 2026-01-14T19:19:56Z – codex – lane=doing – Started implementation
