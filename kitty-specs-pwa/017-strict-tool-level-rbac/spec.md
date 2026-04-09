# Feature Specification: Strict Tool-Level RBAC and Persona Enforcement

**Feature Branch**: `017-strict-tool-level-rbac`
**Created**: 2026-01-21
**Status**: Draft
**Input**: User description: "strict role-based access control: All tools that a LLM can call are now scoped. Scoped by accessibility - a business owner can only access them, or an employee. For example, an employee shouldn't have access to billing, to exporting all customers, to sending invoices, etc. Also, an intelligent assistant must be able to only answer queries as an assistant. Also, I suggest adding a \"Manager\" role, who is able to access all tools except billing."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Restricted Tool Access (Priority: P1)

As an **Employee**, I attempt to use a restricted tool (like creating an invoice or exporting all customers) via the AI assistant, so that the assistant prevents unauthorized administrative actions.

**Why this priority**: Core security requirement to prevent data exfiltration and unauthorized billing by non-admin users.

**Independent Test**: An Employee user sends a message like "Export all customers to CSV" or "Send a $100 invoice to John Doe". The assistant attempts to call the tool and receives a "Permission Denied" result, which it then reports to the user.

**Acceptance Scenarios**:

1. **Given** a user with the `EMPLOYEE` role, **When** they ask to "Send an invoice to Bob", **Then** the assistant tool execution fails with a message: "It seems you are trying to send an invoice. Sorry, you don't have permission for that."
2. **Given** a user with the `EMPLOYEE` role, **When** they ask to "Export all jobs", **Then** the assistant tool execution fails with a message: "It seems you are trying to export jobs. Sorry, you don't have permission for that."

---

### User Story 2 - Manager Access Level (Priority: P1)

As a **Manager**, I want to perform all CRM operations (routing, customer management, job updates) but be restricted from billing operations, so that I can handle operations without having full owner privileges.

**Why this priority**: Enables delegation of operational tasks without exposing sensitive billing/financial controls.

**Independent Test**: A Manager user sends a message to "Optimize today's routes" (Success) and then asks to "Change our subscription plan" or "Process a payment" (Denied).

**Acceptance Scenarios**:

1. **Given** a user with the `MANAGER` role, **When** they ask to "Re-route employee X", **Then** the assistant executes the `AutorouteTool` successfully.
2. **Given** a user with the `MANAGER` role, **When** they ask to "Process a customer payment", **Then** the assistant receives a "Permission Denied" message for the billing tool.

---

### User Story 3 - Persona Enforcement for Non-Owners (Priority: P2)

As an **Associate** (Employee or Manager), I ask the assistant a query that requires reading data I don't have full "status" for, so that the assistant answers but reminds me of my restricted role access.

**Why this priority**: Ensures users are aware of their limited permissions and prevents the assistant from appearing "all-powerful" to unauthorized roles.

**Independent Test**: An Employee asks "What is our total revenue this month?". The assistant retrieves the data but appends the required disclaimer.

**Acceptance Scenarios**:

1. **Given** a user with a role other than `OWNER`, **When** they ask a query about restricted features/data, **Then** the assistant answers the query and appends: "The user does not have role-based access to this feature because he doesn't have a status."

---

### Edge Cases

- **Missing Role**: If a user has no assigned role, the system should default to the most restrictive level (`EMPLOYEE`) or deny all tool access.
- **Friendly Name Translation**: If a tool lacks a defined "friendly name" in the configuration, but is called, the system should gracefully handle the error (perhaps using a fallback or raw name if necessary, though the requirement is for friendly names).
- **Multiple Tool Calls**: If an LLM attempts to call multiple tools in a single turn, some authorized and some not, each should be evaluated independently.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Role Hierarchy: The system MUST support at least three roles: `OWNER`, `MANAGER`, and `EMPLOYEE`.
- **FR-002**: RBAC Configuration: Tool permissions MUST be defined in a hardcoded `rbac_tools.yaml` file.
- **FR-003**: Tool Scoping: Every tool executable by the LLM MUST be mapped to one or more authorized roles.
- **FR-004**: Execution Interceptor: The tool execution layer MUST verify the current user's role against the `rbac_tools.yaml` before executing any tool.
- **FR-005**: Explicit Denial Message: When access is denied, the system MUST return a message to the LLM in the format: `"It seems you are trying to [friendly tool name]. Sorry, you don't have permission for that."`
- **FR-006**: Friendly Tool Naming: Each tool in the RBAC configuration MUST have a human-readable "friendly name" (e.g., "export jobs" instead of `ExportJobsTool`).
- **FR-007**: Persona Disclaimer: If the current user's role is not `OWNER`, the assistant MUST append the following string to its response when discussing restricted features: `"The user does not have role-based access to this feature because he doesn't have a status."`

### Key Entities *(include if feature involves data)*

- **User Role**: An attribute of the User entity determining their access level (`OWNER`, `MANAGER`, `EMPLOYEE`).
- **RBAC Configuration**: A YAML structure mapping tool identifiers to authorized roles and friendly descriptions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of LLM tool calls are checked against the RBAC configuration before execution.
- **SC-002**: Zero unauthorized tool executions occur for `EMPLOYEE` and `MANAGER` roles during security testing.
- **SC-003**: All permission denied messages use the specified friendly format and correct tool names.
- **SC-004**: Assistant responses to non-owners regarding restricted data consistently include the mandatory status disclaimer.
