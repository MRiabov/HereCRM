---
work_package_id: "WP03"
title: "Webhook Dispatcher"
lane: "doing"
subtasks: ["T012", "T013", "T014", "T015"]
dependencies: ["WP01"]
agent: "Antigravity"
shell_pid: "63157"
---

## Objective

Implement the outbound "Generic Webhook" system. When a job is booked, the system should look up active webhook configurations and POST the job details to the configured URLs, signed with an HMAC secret.

## Context

Integrators need to know when a Job is booked.

- **Spec**: `kitty-specs/015-ad-automation-integrations/spec.md` (Sections 4.3, 4.5)

## Subtasks

### T012: Verify and hook into `job.booked` event

**Purpose**: Ensure the system publishes the necessary event.
**Steps**:

1. Check `src/events.py` for a `JOB_BOOKED` event type. If missing, define it.
2. Verify `JobService` emits this event when a job status changes to `BOOKED`.
    - If not, modify `JobService.book_job` (or equivalent) to emit `event_bus.publish(JOB_BOOKED, job)`.

### T013: Create `IntegrationEventHandler` framework

**Purpose**: framework for listening to events and dispatching integration tasks.
**Steps**:

1. Create `src/handlers/integration_handlers.py`.
2. Define `IntegrationEventHandler` class.
3. Method `handle_job_booked(job: Job)`:
    - This method will be the subscriber to the `JOB_BOOKED` event.
    - Annotate with `@event_bus.subscribe(JOB_BOOKED)` (or equivalent syntax).

### T014: Implement generic Webhook dispatch logic

**Purpose**: Send the HTTP requests.
**Steps**:

1. In `IntegrationEventHandler.handle_job_booked`:
    - Call `IntegrationRepository.get_active_by_type(IntegrationType.WEBHOOK)`.
    - Loop through configs.
2. For each config:
    - Extract `url` and `signing_secret` from `config_payload`.
    - Construct payload: `{ "event": "job.booked", "job_id": job.id, "customer": ... }`.
    - Sign payload using `Signer` (from WP02) or `hmac` directly if WP02 not merged (better to reuse if available, otherwise duplicate small logic/import). *Note: Reuse `src/utils/security.py` if available.*
    - Send POST request using `aiohttp` (asynchonous).
    - Handle exceptions (timeout, 500) by logging errors. DO NOT retry for this MVP.

### T015: Add unit tests for Webhook dispatching

**Purpose**: Verify logic without making real HTTP calls.
**Steps**:

1. Create `tests/unit/test_integration_handlers.py`.
2. Mock `IntegrationRepository` to return sample Webhook configs.
3. Mock `aiohttp.ClientSession` (or `httpx` if used).
4. Simulate `handle_job_booked` call.
5. Assert HTTP request was made to the correct URL with correct body and `X-HereCRM-Signature` header.

## Definition of Done

- `JOB_BOOKED` event is confirmed/implemented.
- `IntegrationEventHandler` successfully receives the event.
- Webhooks are sent to external URLs with valid signatures.
- Tests pass with mocked network calls.

## Activity Log

- 2026-01-22T10:45:58Z – Antigravity – shell_pid=63157 – lane=doing – Started implementation via workflow command
