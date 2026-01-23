---
lane: "for_review"
agent: "Antigravity"
shell_pid: "6756"
---

# Work Package 06: TextGrid Integration & Refactor

**Goal**: Integrate TextGrid and refactor SMS support.
**Spec**: [Spec 009](../spec.md) (WP06)

## Context

We want to add support for **TextGrid** as an alternative (and default) SMS provider because it is significantly cheaper than Twilio.
Currently, `TwilioService` is the only implementation. We need to introduce an abstraction layer (`SMSMessagingService`) to allow switching between Twilio and TextGrid.

## Requirements

1. **Core Abstraction**:
    - Create `src/services/channels/base.py` defining an abstract base class `SMSMessagingService`.
    - It must define the standard interface for sending SMS: `async def send_sms(self, to_number: str, body: str) -> bool`.
    - It should include common validation logic (e.g., E.164 check).

2. **Configurations**:
    - Update `src/config/__init__.py`:
        - Add TextGrid settings to `Settings` class:
            - `textgrid_account_sid` (Optional[str])
            - `textgrid_auth_token` (Optional[str])
            - `textgrid_phone_number` (Optional[str])
        - Update `ChannelSettings` model to include `provider: Optional[str] = None`.
    - Update `src/config/channels.yaml` (if it exists, or the default in `load_channels_config`) to include a `provider` field for `sms` (defaulting to 'textgrid').

3. **Refactor Twilio**:
    - Modify `src/services/twilio_service.py`:
        - Make `TwilioService` inherit from `SMSMessagingService`.
        - Ensure it implements the interface correctly.

4. **Implement TextGrid**:
    - Create `src/services/channels/textgrid.py`.
    - Implement `TextGridService` inheriting from `SMSMessagingService`.
    - Use `requests` (or `httpx`) to call the TextGrid API. If no official SDK implies simple REST calls.
    - Assume basic TextGrid API structure (check docs or assume similar to Twilio but check correct endpoint). *Note: Since TextGrid is a specific service, if docs aren't provided, use a placeholder implementation or standard REST pattern and ask for docs if authentication fails.* - **Actually, assume standard Twilio-compatible API or standard REST API.**  *Clarification: TextGrid often advertises Twilio compatibility or a specific API. We will implement a generic REST client for it.*

5. **Service Factory**:
    - Create `src/services/sms_factory.py`.
    - Implement `get_sms_service() -> SMSMessagingService`.
    - Logic:
        - Load config (channel settings).
        - If `sms.provider` == 'twilio', return `TwilioService()`.
        - If `sms.provider` == 'textgrid', return `TextGridService()`.
        - Default to 'textgrid'.

6. **Integration**:
    - Search for usages of `TwilioService` (likely in `src/tool_executor.py`, `src/services/messaging_service.py`).
    - Replace direct instantiation with `get_sms_service()`.

## Files to Create/Edit

- `src/services/channels/base.py` (New)
- `src/services/channels/textgrid.py` (New)
- `src/services/sms_factory.py` (New)
- `src/services/twilio_service.py` (Edit)
- `src/config/__init__.py` (Edit)
- `src/tool_executor.py` (Edit - check usage)
- `src/services/messaging_service.py` (Edit - check usage)

## Testing

- Create a test script `scripts/test_sms.py` that attempts to send an SMS using the factory.
- It should print which provider is being used.

## Implementation Steps

1. **Config**: Add `textgrid_*` fields to `Settings` in `src/config/__init__.py`. Update `ChannelSettings` to accept `provider`.
2. **Base Class**: Create `src/services/channels/base.py` with `SMSMessagingService(ABC)`.
3. **Refactor Twilio**: Update `TwilioService` to inherit from `SMSMessagingService`.
4. **TextGrid Service**: Create `TextGridService`. define `send_sms` logic.
5. **Factory**: Create `src/services/sms_factory.py`.
6. **Wire up**: Find all refs to `TwilioService` and replace with factory call.
7. **Verify**: Run `scripts/test_sms.py`.

## Activity Log

- 2026-01-23T09:15:18Z – Antigravity – shell_pid=6756 – lane=doing – Started implementation via workflow command
- 2026-01-23T09:20:13Z – Antigravity – shell_pid=6756 – lane=for_review – Integrated TextGrid as default SMS provider and refactored SMS support with factory abstraction.
