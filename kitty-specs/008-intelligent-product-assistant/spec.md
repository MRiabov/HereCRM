# Feature Specification: Intelligent Product Assistant & Documentation

**Feature Branch**: `008-intelligent-product-assistant`  
**Created**: 2026-01-18  
**Status**: Draft  
**Input**: User documentation and a LLM RAG assistant. "how do I add a lead?", "why did my last prompt fail", "what can I do to use you better?". Access to last 5 messages/tool calls.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - "How-To" Guidance (Priority: P1)

As a user, I want to ask "How do I add a lead?" or "How do I schedule a job?" so that I can learn how to use the CRM features without reading a long manual.

**Why this priority**: Essential for onboarding and user retention. Reduces friction for new users.

**Independent Test**: Can be tested by sending "How do I add a lead?" and verifying the response contains instructions from the manual.

**Acceptance Scenarios**:

1. **Given** a product manual exists, **When** user asks "How do I add a lead?", **Then** assistant responds with the specific steps from the manual.
2. **Given** a product manual exists, **When** user asks about a featue not in the manual, **Then** assistant politely states it doesn't know and suggests checking available commands.

---

### User Story 2 - Interaction Troubleshooting (Priority: P1)

As a user, I want to ask "Why did my last prompt fail?" or "Why didn't you add that job?" so that I can understand what went wrong and how to format my request better.

**Why this priority**: Crucial for building trust and helping users correct their input patterns.

**Independent Test**: Can be tested by intentionally sending an ambiguous message (e.g., "Add job") followed by "Why did that fail?".

**Acceptance Scenarios**:

1. **Given** the last user message resulted in a parsing error or clarification request, **When** user asks "Why did it fail?", **Then** assistant explains the missing information (e.g., "The message didn't contain a customer name").
2. **Given** the last 5 messages are available, **When** user asks "What can I do to use you better?", **Then** assistant provides suggestions based on recent interaction patterns and the manual.

---

### User Story 3 - Capability Discovery (Priority: P2)

As a user, I want to ask "What can I do?" or "Show me what you can do" so that I can explore the system's capabilities.

**Why this priority**: Helps users discover features they haven't used yet.

**Independent Test**: Can be tested by asking "What can you do?" and verifying it lists key CRM functions (leads, jobs, search, etc.).

**Acceptance Scenarios**:

1. **Given** a product manual exists, **When** user asks "What can I do?", **Then** assistant provides a high-level summary of supported actions (Adding leads, scheduling jobs, searching, etc.).

---

### Edge Cases

- **History empty**: If a new user asks "Why did my last prompt fail?", assistant should handle the lack of history gracefully (e.g., "I don't have enough context yet. Try asking how to do something specific!").
- **Manual missing**: System should have a fallback help message if the RAG document is unavailable.
- **Ambiguous failure**: If the LLM itself failed (e.g., API error), the assistant should explain that it was a system error rather than a user input error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an intelligent assistant accessible via a tool call (triggered by keywords like "help", "how to", "why did...").
- **FR-002**: Assistant MUST use RAG or prompt-injection over a markdown documentation file (`manual.md`).
- **FR-003**: System MUST fetch the last 5 messages (user and assistant) and their associated metadata (tool calls, error logs) from the database to provide context.
- **FR-004**: Assistant MUST be able to explain failed parsing attempts (when `LLMParser` returns `error_unclear_input` or a clarification request).
- **FR-005**: Assistant MUST provide concise responses suitable for WhatsApp (limit length, avoid complex formatting).
- **FR-006**: Assistant MUST prioritize information from the product manual for "how-to" queries.
- **FR-007**: System MUST provide a `HelpTool` that triggers this assistant flow.

### Key Entities *(include if feature involves data)*

- **Message**: Represents previous interactions stored in the database, including role (user/assistant), body, and `log_metadata` (containing tool call details).
- **Product Manual**: A markdown file(s) containing feature descriptions and usage guides.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Assistant correctly identifies the cause of 4 out of 5 common parsing failures in test sets.
- **SC-002**: Answers to "How-To" questions are strictly derived from the manual (no hallucination of unsupported features).
- **SC-003**: Help responses are delivered within 5 seconds of the user's request.
- **SC-004**: User "re-try" success rate increases (users successfully format requests after being told why they failed).
