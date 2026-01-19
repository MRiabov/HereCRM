# Implementation Plan - Intelligent Product Assistant (Spec 008)

# Goal Description

Implement an intelligent RAG-based assistant that answers user questions ("How do I add a lead?", "Why did it fail?") by using the Product Manual and conversation history. This replaces the static help message with dynamic, context-aware guidance.

## User Review Required
>
> [!IMPORTANT]
> **Configuration File**: I will be creating a new `src/assets/channels.yaml` file to control response lengths. Please confirm this location is acceptable.

## Proposed Changes

### Configuration & Assets

#### [NEW] [channels.yaml](file:///home/maksym/Work/proj/HereCRM/src/assets/channels.yaml)

- Define defaults for `whatsapp` (shorter) and `email` (longer) response styles.

### Core Logic

#### [MODIFY] [config.py](file:///home/maksym/Work/proj/HereCRM/src/config.py)

- Add `ChannelConfig` models.
- Load `channels.yaml` into settings.

#### [NEW] [help_service.py](file:///home/maksym/Work/proj/HereCRM/src/services/help_service.py)

- **Responsibility**: Orchestrate the RAG flow.
- **Methods**:
  - `get_help_response(user_phone: str, query: str, channel: str = "whatsapp") -> str`
  - Fetches `manual.md` (cached).
  - Fetches last 5 messages via `MessageRepository`.
  - Constructs system prompt with Manual + History + formatted "How to answer" guidelines.
  - Calls `LLMClient` for completion.

#### [MODIFY] [llm_client.py](file:///home/maksym/Work/proj/HereCRM/src/llm_client.py)

- Add `chat_completion(messages, model)` method.
- Current methods (`parse`) are specialized for Tool calling. We need a raw text generation method for the Help Assistant.

### Integration

#### [MODIFY] [whatsapp_service.py](file:///home/maksym/Work/proj/HereCRM/src/services/whatsapp_service.py)

- Initialize `HelpService`.
- In `handle_message`, when `HelpTool` is detected, call `self.help_service.get_help_response(...)` instead of `template_service.render("help_message")`.

#### [MODIFY] [tool_executor.py](file:///home/maksym/Work/proj/HereCRM/src/tool_executor.py)

- Updates to `HelpTool` logic if needed (currently it just returns a string, but the main logic is in `WhatsappService` interception).

## Verification Plan

### Automated Tests

- **Unit Tests**:
  - `tests/test_help_service.py`: Mock `LLMClient` and `MessageRepository`. Verify prompt construction includes Manual and History.
  - Test `ChannelConfig` loading.
- **Run Command**:

    ```bash
    pytest tests/test_help_service.py
    ```

### Manual Verification

1. **Setup**:
    - Ensure `manual.md` exists.
    - Run app: `fastapi dev src/main.py`
2. **Scenario 1: General Help**
    - Send: "How do I add a lead?"
    - **Expect**: Assistant explains the syntax from the manual (e.g., "Add new lead: Name, Phone").
3. **Scenario 2: Context Awareness**
    - Send: "Add job for" (incomplete) -> System errors/asks clarification.
    - Send: "Why did that fail?"
    - **Expect**: Assistant explains missing name/details based on the previous message history.
4. **Scenario 3: Channel Config**
    - Verify response is concise (WhatsApp default).
