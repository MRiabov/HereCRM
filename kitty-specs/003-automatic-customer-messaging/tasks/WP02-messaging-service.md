---
work_package_id: WP02
subtasks:
  - T004
  - T005
  - T006
  - T007
lane: "doing"
agent: "codex"
---

# Work Package 02: Messaging Service Infrastructure

## Goal

Implement the `MessagingService` that consumes events and sends messages via WhatsApp/SMS (initially mocked or logged).

## Context

The core logic of the feature lives here. The service listens to the Event Bus (via T007), processes requests, and handles the actual sending mechanism.

## Subtasks

### T004: Create MessagingService class

- **File**: `src/services/messaging_service.py`
- **Description**: scaffolding for the service. Should have an `asyncio.Queue` for buffering messages if needed, or handle directly async.

### T005: Implement send_message logic

- **File**: `src/services/messaging_service.py`
- **Description**: `async def send_message(self, recipient, content, channel="whatsapp") -> MessageLog`.
- **Logic**:
  - Create `MessageLog` entry with status PENDING.
  - (Mock) Send message / Call external API.
  - Update `MessageLog` status to SENT/FAILED.
  - Return `MessageLog`.

### T006: Implement async queue consumer

- **Description**: If high volume is expected, implement a background worker to process the queue. For MVP, direct async processing might suffice, but plan mentions `asyncio.Queue`.
- **Implementation**: `process_queue()` method that runs forever.

### T007: Register MessagingService as listener

- **Description**: In the main application startup (e.g., `main.py` lifespan or `tool_executor.py` initialization), ensure `MessagingService` subscribes to relevant events on the `EventBus`.

## Verification

- Unit test `MessagingService.send_message` ensuring it creates DB records.
- Integration test: Emit an event and verify `MessagingService` picks it up (after T007).

## Activity Log

- 2026-01-14T20:59:38Z – codex – lane=doing – Started implementation
