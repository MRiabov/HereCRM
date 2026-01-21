# Feature Specification: Conversational Customer Billing & Addons

**Feature Branch**: `010-conversational-billing`  
**Created**: 2026-01-20  
**Status**: Draft  
**Input**: User description: "customer billing: in 'settings'->'billing settings' users can see their a) billing status b) an option to add employees (expand seats, for a price) c) an option to add addons. Addons expand functionality like 1. Employee management addon 2. Customer campaign messaging addon 3. Etc. configurable via yaml. Tools require a 'scope'. Users can request 'add [addon name] to my subscription' which prompts payment. Payment procedure: 1. User requests pay. 2. App calculates total. 3. App sends subtotal and link. 4. Stripe link. 5. Automatic registration."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Billing Status (Priority: P1)

As a business owner, I want to check my current subscription status, including seats and active addons, by typing "billing" or "billing settings" in the chat, so that I know what I'm paying for.

**Why this priority**: Essential for visibility and entry point to other billing actions. Without this, users cannot see what they have or need.

**Independent Test**: Can be tested by simulating "billing" command for users with different states (free tier, paid seats, active addons) and verifying the response correctly outlines their current package.

**Acceptance Scenarios**:

1. **Given** a user is in "idle" or "settings" state, **When** they type "billing", **Then** the system enters BILLING state and replies with a summary of their current plan, number of seats, and active addons.
2. **Given** a user with 5 seats and "Campaign Messaging" addon, **When** they request billing status, **Then** the response explicitly lists "5 Seats" and "Campaign Messaging: Active".

---

### User Story 2 - Automated Payment & Provisioning Flow (Priority: P1)

As a user, I want to pay for upgrades via a secure link and have the features enabled immediately, so that I don't have to contact support or leave the chat context to upgrade.

**Why this priority**: Critical path for revenue. If users can't pay or features don't unlock, the upsell feature is useless.

**Independent Test**: Can be tested by mocking the payment generation and webhook receipt, verifying that the database updates the business's entitlements automatically.

**Acceptance Scenarios**:

1. **Given** a pending upgrade request (e.g., adding a seat), **When** the user confirms they want to pay, **Then** the system calculates the prorated total and provides a Stripe payment link.
2. **Given** a successful payment event from Stripe, **When** the webhook is received, **Then** the system automatically updates the business record to include the new seat/addon and notifies the user (if possible) or reflects it in the next status check.

---

### User Story 3 - Expand Seats (Priority: P2)

As a growing business, I want to add more seats to my subscription through the chat, so that I can onboard new employees (like salespeople) without administrative friction.

**Why this priority**: Key scaling metric and revenue driver.

**Independent Test**: Can be tested by requesting "add 2 seats", verifying the payment flow, and checking if the allowed user limit for the business increases.

**Acceptance Scenarios**:

1. **Given** I am in BILLING state, **When** I say "add 2 seats", **Then** the system quotes the price for the additional seats and asks for confirmation to generate a payment link.
2. **Given** I have purchased extra seats, **When** I try to add a new user to my business, **Then** the system allows it up to the new limit (validating the purchase worked).

---

### User Story 4 - Purchase Feature Addons (Priority: P2)

As a business owner, I want to add capabilities like "Employee Management" or "Campaign Messaging" to my account, so that I can access advanced tools.

**Why this priority**: Unlocks advanced functionality partitioned by the new "scope" system.

**Independent Test**: Can be tested by requesting various addons defined in the YAML config and verifying they render correctly in the billing summary and unlock associated permissions.

**Acceptance Scenarios**:

1. **Given** I am in BILLING state, **When** I say "list addons", **Then** the system shows available addons from the configuration (e.g., Employee Management, Campaign Messaging) with prices.
2. **Given** I request "add Campaign Messaging", **When** I complete payment, **Then** the addon is marked as 'Active' on my account.

---

### User Story 5 - Tool Scope Enforcement (Priority: P1)

As the system administrator, I want specific tools to be restricted to businesses with the corresponding addon, so that premium features are properly gated.

**Why this priority**: Ensures monetization logic works. If tools work without paying, the billing system is moot.

**Independent Test**: Can be tested by trying to invoke a "scoped" tool (e.g., a campaign tool) with and without the required addon in the business's profile.

**Acceptance Scenarios**:

1. **Given** a business WITHOUT the "Campaign Messaging" addon, **When** a user tries to use a campaign-related tool, **Then** the tool execution is blocked, and the system informs the user they need the "Campaign Messaging" addon.
2. **Given** a business WITH the addon, **When** the user invokes the tool, **Then** it executes successfully.
3. **Given** a "Standard" tool (no scope), **When** any user invokes it, **Then** it works regardless of addons.

---

### User Story 6 - Usage Tracking & Overage Billing (Priority: P1)

As a business owner, I want to know how many messages I've sent and be billed automatically for overages, so that I don't get service interruptions while paying for what I use.

**Why this priority**: Essential for cost recovery (SMS/WhatsApp costs).

**Independent Test**: Can be tested by simulating sending 1001 messages and verifying the billing status shows overage and the estimated cost increases.

**Acceptance Scenarios**:

1. **Given** a business has sent 500 messages this month (under 1000 limit), **When** they check billing status, **Then** it shows "Messages: 500/1000 (Included)".
2. **Given** a business has sent 1050 messages, **When** they check billing status, **Then** it shows "Messages: 1050 (50 overage). Estimated Overage Cost: $1.00".
3. **Given** the billing cycle ends, **When** the invoice is generated, **Then** it includes the $1.00 overage charge.

---

### Edge Cases

- **Payment Failure**: What happens if the user clicks the link but the payment fails or is cancelled? (System should assume no change until successful webhook).
- **Concurrent Updates**: What occurs if two admins specified for the same business try to update billing simultaneously? (Database transactions should handle this, last write or additive logic).
- **Pro-ration Complexity**: How are mid-cycle additions calculated? (MVP: Simply charge a calculated "pending" amount passed from the app logic, or rely on Stripe's proration if using Subscriptions API. For MVP, we will assume the app calculates a specific "pay now" amount for the remainder or a fixed setup fee, as specified "app calculates total").
- **Addon Removal**: How do users downgrade? (MVP: Instruct them to contact support, or "remove addon" command that cancels at period end).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a conversational state `BILLING` accessible via "settings" or direct command.
- **FR-002**: System MUST load available addons, prices, and their required scopes from a configuration file (`billing_config.yaml` or similar).
- **FR-003**: System MUST store a business's "subscription status" including: Plan Tier, Seat Count, and List of Active Addons.
- **FR-004**: System MUST implement a `Scope` check mechanism in the Tool Executor or Service layer that validates if the calling business possesses the required scope for a tool before execution.
- **FR-005**: System MUST be able to calculate a total price for a requested upgrade (Seats * Price + Addon Price) and generate a Stripe Payment Link.
- **FR-006**: System MUST expose a generic webhook endpoint (or specific Stripe endpoint) to receive `checkout.session.completed` (or similar) events and update the business's entitlements securely.
- **FR-007**: System MUST allow adding "Seats" independently of "Addons".
- **FR-008**: System MUST provide a clear confirmation message with the total amount before generating the payment link.
- **FR-009**: System MUST track the number of outgoing messages per business per billing cycle.
- **FR-010**: System MUST include the first 1000 messages per month in the base plan at no extra cost.
- **FR-011**: System MUST charge $0.02 per message for every message exceeding the 1000 message limit.
- **FR-012**: System MUST display current message usage and estimated overage costs in the billing status response.

### Key Entities

- **BusinessSubscription**: Extends valid `Business` model or new related entity. Tracks `seat_limit`, `active_addons` (JSON list or relationship), `stripe_customer_id`, `subscription_status`.
- **AddonConfig**: In-memory representation of the YAML config (id, name, description, price, required_scope).
- **ToolDefinition**: Updates existing tool definitions to include an optional `required_scope` field.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view their correct quota and addon status within 1 interaction ("billing").
- **SC-002**: Users can generate a valid payment link for an upgrade within 3 conversational turns.
- **SC-003**: 100% of tool invocations requiring a scope are blocked for non-compliant businesses.
- **SC-004**: Valid payment webhooks result in updated business entitlements in the database within 5 seconds of receipt.
