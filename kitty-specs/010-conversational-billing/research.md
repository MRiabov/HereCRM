# Research & Decisions: Conversational Billing

**Date**: 2026-01-20
**Feature**: Conversational Billing & Addons
**Status**: Consolidated

## Key Decisions

### 1. Payment Integration Strategy

**Decision**: Use **Stripe Subscriptions** with "Pending Updates" for upgrades.
**Rationale**: The user requirement ("App calculates total... Sends Link") maps perfectly to the Stripe `payment_behavior='pending_if_incomplete'` flow.

- A "Checkout Session" is best for the *initial* subscription.
- An "Invoice" (via subscription modification) is best for *upgrades*.
**Flow**:

1. **Initial**: Bot sends Stripe Checkout Link (`mode='subscription'`).
2. **Upgrade**:
   - Backend calculates change.
   - Calls `stripe.Subscription.modify(..., payment_behavior='pending_if_incomplete', proration_behavior='always_invoice')`.
   - This keeps the change "pending" until paid.
   - Backend extracts `hosted_invoice_url` from the new invoice.
   - Bot sends this link.
   - Webhook `invoice.payment_succeeded` finalizes the state.

### 2. Data Model & Configuration

**Decision**: Hybrid Approach.

- **Static Config**: `billing_config.yaml` for Addon definitions (Price IDs, Names, Scopes). This allows easy updates without DB migrations for every new addon.
- **Dynamic State**: `Business` table stores `stripe_customer_id`, `stripe_subscription_id`, `seat_count`, and `active_addons` (JSON list of scopes).
- **Justification**: Scopes are code-level concepts. Mapping them in a YAML file to Stripe Price IDs is the most flexible way to manage the catalog.

### 3. Tool Access Control

**Decision**: Decorator or Middleware in `ToolExecutor`.
**Implementation**:

- The `ToolExecutor` seems to manually route based on tool type.
- We will add a helper `_check_scope(required_scope)` in `ToolExecutor`.
- Before executing a tool that needs a scope, this helper ensures the `Business` has it.

### 4. Proration Handling

**Decision**: Rely on Stripe's default `proration_behavior='create_prorations'`.

- This ensures the user pays only for the remainder of the cycle.
- The generated invoice will reflect this precise amount, satisfying the "App calculates total" requirement.

## Open Questions Resolved

- **Mid-month billing**: Solved by Stripe Prorations.
- **Link generation**: Solved by `hosted_invoice_url`.
