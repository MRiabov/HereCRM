# Research: Multi-channel Communication

## Unknowns & Clarifications

### Auto-Confirmation Logic

- **Question**: How to implement the 45-second timeout?
- **Decision**: Hybrid approach.
  - **Persistent**: Background worker checks for "stale" pending actions on startup/periodic interval (e.g. every minute).
  - **Async**: In-memory timer for immediate execution if the service remains up.
- **Rationale**: Robustness against restarts while maintaining responsiveness.

### Identity Merging

- **Question**: How to handle users using multiple channels?
- **Decision**: Separate identities unless explicit match provided.
- **Micro-decision**: If an email comes in that matches a `User.email`, link it. Same for phone. Explicit merging logic out of scope for MVP.

### Webhook Schema

- **Decision**: JSON payload with `channel`, `identity`, `content`, `metadata`.
- **Schema**:

  ```json
  {
    "channel_type": "webhook",
    "identity": "user@example.com",
    "content": "Hello world",
    "metadata": { ... }
  }
  ```

## Technology Decisions

1. **SMS Provider**: Twilio (User specified).
2. **Email Provider**: Postmark (User specified).
3. **Database**: PostgreSQL (Existing).
4. **State Machine**: Enhanced `ConversationState` with `pending_action_timestamp` and `channel_type`.

## Best Practices

- **Twilio**: Use Messaging Services for better delivery/sender ID handling.
- **Postmark**: Use inbound webhook parsing streams.
- **Privacy**: Ensure PII in webhooks is handled according to existing policies.
