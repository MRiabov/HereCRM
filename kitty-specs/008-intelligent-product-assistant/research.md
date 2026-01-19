# Research: Intelligent Product Assistant

## 1. RAG Approach: Prompt Injection

**Decision**: Use **Prompt Injection** for the Product Manual.
**Rationale**:

- The manual (`manual.md`) is relatively small (< 50KB).
- Current LLM context windows (e.g., Llama 3.1 8B ~128k tokens) can easily fit the entire manual.
- Prompt injection is simpler to implement and maintain than a dedicated Vector DB (Chroma/Pinecone) for this scale.

## 2. Configuration Strategy

**Decision**: Use **YAML** file for channel settings + **Pydantic** model in code.
**Rationale**:

- Separation of concerns: Non-technical users can edit `channels.yaml` to adjust response lengths.
- Traceability: `src/config.py` using `pydantic_settings` is already established.
- **Structure**:

  ```yaml
  channels:
    whatsapp:
      max_length: 500
      style: "concise"
    email:
      max_length: 2000
      style: "formal"
  ```

## 3. Architecture Change

**Decision**: Introduce `HelpService` to encapsulate RAG logic.
**Rationale**:

- `WhatsappService` is already large (600+ lines). Adding RAG logic (fetching history, formatting manual, specialized prompting) there would violate Single Responsibility Principle.
- `HelpService` will:
    1. Fetch `manual.md`.
    2. Fetch last 5 messages from `MessageRepository`.
    3. Construct the RAG prompt.
    4. Call `LLMClient` (new method `chat_completion` needed, as `parse` is for tools).
    5. Return the text response.

## 4. Sub-agent / Recursive Calls

**Decision**: The "Help Assistant" is effectively a sub-agent call.

- It uses a different system prompt (injected manual).
- It doesn't use the standard Tool definitions (it's a pure text response, though it *could* hypothetically use navigation tools, specs limit it to "answering questions"). FR-002 implies text guidance.

## 5. Entry Point

- `HelpTool` is identified by `LLMParser` in the main flow.
- `WhatsappService` intercepts `HelpTool` (lines 176-177) and currently calls `_generate_help_message` (static template).
- **Change**: Replace `_generate_help_message` logic to call `HelpService.get_response(user_query)`.
