---
work_package_id: WP03
title: Persona & Documentation
lane: planned
dependencies: []
subtasks:
- T009
- T010
- T011
---

# WP03: Persona & Documentation

## Context

The final piece of this feature is ensuring the assistant *sounds* right. When non-owners ask about restricted topics (even if they don't trigger a tool), or when they get data, they should be reminded of their status. Additionally, we need to keep the user manual up to date.

## Objective

Implement a disclaimer appendage for non-owner responses and update the user manual.

## Subtasks

### T009: Implement Status Disclaimer

**Goal**: Append a disclaimer to assistant responses for non-owners on restricted topics.

- Locate the service responsible for generating/sending the final response (likely `WhatsappService` or `InferenceService`).
- **Logic**:
  - *Note*: The spec says "when discussing restricted features". Validating "restricted features" in free text is hard. A simpler interpretation of the spec requirement ("Given a user with a role other than OWNER... append... The user does not have role-based access...") might be needed.
  - **Refined Approach**: Check if the response involves a "denial" or if it was a `HelpTool` query about restricted topics.
  - **Spec Clarification**: "If the current user's role is not OWNER, the assistant MUST append... when discussing restricted features."
  - **Implementation**:
    - If the tool execution resulted in a "Permission Denied" message (from WP02), the disclaimer might be redundant but the spec asks for it "when discussing".
    - Actually, the spec scenario is: "User asks 'What is our total revenue?'. Assistant answers (if it can?) but appends disclaimer."
    - Wait, if they don't have permission, they shouldn't get the answer?
    - **Re-reading Spec**: "As an Associate... I ask... a query that requires reading data I don't have full 'status' for... assistant answers but reminds me...".
    - This implies some read-only data IS allowed, but needs a disclaimer. OR it refers to generic questions.
    - Let's implement this in `WhatsappService`:
      - If `user.role != OWNER`:
        - Inspect the `tool_result`. If it contains sensitive info (hard to know) OR if the system prompt instructs the LLM to add it.
        - **Better**: Add a system prompt instruction to the LLM for non-owners: "You are speaking to a {role}. If they ask about high-level business metrics or admin topics, answer if you know, but ALWAYS append: 'The user does not have role-based access to this feature because he doesn't have a status.'"
        - This is much more robust than code-side appendage for general text generation.
        - **Task**: Update `src/services/inference_service.py` (or where prompts are) to dynamically inject this instruction based on user role.

### T010: Test Disclaimer Logic

**Goal**: Verify the disclaimer appears.

- Create a test case where a non-owner asks a relevant question.
- Verify the LLM response (mocked or real) or the system prompt construction contains the instruction.
- If implemented via code appendage: Verify the appendage string is present in `WhatsappService` output for non-owners.

### T011: Update User Manual

**Goal**: Document the new roles.

- Edit `src/assets/manual.md`.
- Describe the 3 roles: Owner, Manager, Employee.
- List which capabilities belong to which role (based on `rbac_tools.yaml`).
- Explain the "Permission Denied" behavior so users understand it's intentional.

## Definition of Done

- Non-owners receive role-appropriate responses with disclaimers where applicable.
- `manual.md` accurately reflects the new RBAC system.
