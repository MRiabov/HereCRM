# Research: 003 Automatic Customer Messaging

## Decisions

### 1. Messaging Infrastructure

- **Decision**: Use Python's `asyncio.Queue` for internal message dispatching.
- **Rationale**: User requested a lightweight approach ("Python internal queue") for this iteration. Simpler to implement and sufficient for current scale.
- **Trade-offs**: Non-persistent (messages lost on restart), but acceptable for "quick" notifications.

### 2. WhatsApp Provider

- **Decision**: Meta Cloud API (Direct Integration).
- **Rationale**: User preference ("Meta cloud API"). Official, widely supported, and cost-effective.
- **Alternatives**: Twilio (rejected due to preference).

### 3. Event Architecture

- **Decision**: Internal `EventBus` with publish/subscribe pattern.
- **Rationale**: Decouples business logic (e.g., booking a job) from messaging logic. Allows for easy addition of new subscribers later.

## Open Questions Resolved

- **Persistence**: Not required for this phase.
- **Triggers**: "On My Way", "Job Booked", "Job Scheduled", "Daily Schedule".
