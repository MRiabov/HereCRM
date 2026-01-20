# Implementation Plan: Conversational Customer Billing & Addons

*Path: kitty-specs/010-conversational-billing/plan.md*

**Branch**: `010-conversational-billing` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/010-conversational-billing/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `.kittify/templates/commands/plan.md` for the execution workflow.

The planner will not begin until all planning questions have been answered—capture those answers in this document before progressing to later phases.

## Summary

Implement a conversational billing system integrated with Stripe Subscriptions. Key features include: a new `BILLING` state in the chat bot, capability to view subscription status (seats, active addons), and a flow to upgrade subscriptions (add seats/addons) by generating Stripe Checkout Sessions (or Billing Portal deep links) with automatic proration. Enforce feature access via a "scope" check in the `ToolExecutor`.

## Technical Context

**Language/Version**: Python 3.12 (inferred)
**Primary Dependencies**: Stripe Python SDK, SQLAlchemy (DB), FastAPI (Webhooks).
**Storage**: PostgreSQL (existing `Business` table update, new `BusinessSubscription` logic/fields).
**Testing**: pytest (mocking Stripe API).
**Target Platform**: Linux server / Containerized.
**Project Type**: Web Application + Background Services.
**Performance Goals**: <2s response for billing status; <5s for payment link generation.
**Constraints**: Secure handling of payment webhooks (`customer.subscription.updated`). "MVP" approach using Stripe Checkout for upgrades.
**Scale/Scope**: New domain logic (Billing), integration (Stripe), new bot state.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 1. LLM-First Text Processing

* **Compliance**: Yes. All billing inquiries ("billing status", "add seat") are processed via the LLM to trigger tools.

### 2. Mandatory User Confirmation

* **Compliance**: Yes. The "upgrade" action results in a Payment Link. The actual confirmation is the user paying on the hosted Stripe page. No automatic charges happen without user interaction (initial setup/upgrade).

## Project Structure

### Documentation (this feature)

```text
kitty-specs/010-conversational-billing/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/
├── models.py            # Update Business model
├── services/
│   ├── billing/         # New BillingService (Stripe wrapper)
│   └── crm_service.py   # Integration point
├── api/
│   └── webhooks/        # stripe_webhook.py
└── tool_executor.py     # Add scope enforcement logic

tests/
├── unit/                # Test BillingService
└── integration/         # Test Webhooks
```

**Structure Decision**: Extending existing Single Project structure.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
