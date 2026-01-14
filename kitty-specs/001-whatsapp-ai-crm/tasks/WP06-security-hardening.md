---
lane: "done"
agent: "codex"
---
# Task: WP06 - Security Hardening

Protect the WhatsApp AI CRM against common security risks, including SQL injection, prompt injection, and unauthorized data access.

## Context

The application uses SQLAlchemy for database interactions, which provides baseline protection against SQL injection. However, we need to ensure all inputs are validated, rate limits are in place, and the LLM parser is resilient against manipulation.

## Requirements

### 1. Rate Limiting

- Implement rate limiting for the `/webhook` endpoint.
- Use a simple in-memory or Redis-based (if available) limiter. For this phase, a simple in-memory implementation or `slowapi` is acceptable.
- Limit requests per phone number to prevent spam and LLM abuse.

### 2. Input Validation & Sanitization

- Add length constraints to `WebhookPayload` (e.g., `body` max 1000 characters).
- Validate LLM tool arguments (e.g., `AddJobTool` fields length checks).
- Implement an allowlist for `UpdateSettingsTool` keys (e.g., `['confirm_by_default', 'theme', 'language']`).

### 3. Prompt Injection Defense

- Update the system prompt/instructions for the Gemini model in `LLMParser`.
- explicitly instruct the model to ignore any "ignore previous instructions" or "system override" attempts.
- Ensure the model strictly returns function calls for the defined tools.

### 4. Information Leakage Prevention

- Review `api/routes.py` and services to ensure generic error messages are returned to the client.
- Ensure sensitive data (phone numbers, full names) is not logged in non-debug logging levels.

### 5. Multi-Tenant Scoping Audit

- Create a test or script that scans the repository layer to ensure `business_id` is used in all queries.
- Add a comprehensive test suite `tests/test_security.py` that attempts:
  - SQL injection via search queries.
  - Accessing data from another business ID.
  - Prompt injection attempts.
  - Exceeding rate limits.

## Success Criteria

- [ ] Rate limiting blocks requests exceeding the threshold.
- [ ] Inputs exceeding length limits are rejected/truncated.
- [ ] `UpdateSettingsTool` rejects keys not in the allowlist.
- [ ] `tests/test_security.py` passes all scenarios.
- [ ] No raw SQL usage (`text()`) is found in the codebase.

## Activity Log

- 2026-01-13T21:22:10Z – codex – lane=doing – Started implementation
- 2026-01-13T21:26:19Z – codex – lane=for_review – Ready for review
- 2026-01-13T21:27:16Z – antigravity – lane=done – Approved without changes
