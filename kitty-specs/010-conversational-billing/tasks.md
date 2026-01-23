# Tasks: Conversational Billing & Addons

## WP00: Foundation & Data Model

- [x] **T001**: Install `stripe` python package, add to `pyproject.toml`, and update `.venv`. <!-- id: 0 -->
- [x] **T002**: Create `src/config/billing_config.yaml` with product definitions for seats and addons (names, prices, Stripe price IDs). <!-- id: 1 -->
- [x] **T003**: Update `src/models.py`: Add `BILLING` to `ConversationStatus` enum. <!-- id: 2 -->
- [x] **T004**: Generate Alembic migration to add `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, `seat_limit`, and `active_addons` (JSON) to `businesses` table. <!-- id: 3 -->
- [x] **T005**: Update `Business` SQLAlchemy model in `src/models.py` and `BusinessRepository` in `src/repositories.py` to support new fields. <!-- id: 4 -->

## WP01: Billing Service Logic

- [ ] **T006**: Create `src/services/billing_service.py` with `BillingService` class and basic Stripe initialization using environment variables. <!-- id: 5 -->
- [ ] **T007**: Implement `get_billing_status(business_id)` to return current quota, status, and active addons. <!-- id: 6 -->
- [ ] **T008**: Implement `create_checkout_session` (for first-time subscription) and `create_upgrade_link` (for adding seats/addons to existing subscription with proration). <!-- id: 7 -->
- [ ] **T009**: Add unit tests in `tests/test_billing_service.py` mocking Stripe API calls. <!-- id: 8 -->

## WP02: Webhook Handling

- [x] **T010**: Create `src/api/webhooks/stripe_webhook.py` FastAPI router and endpoint to receive Stripe events with signature validation. <!-- id: 9 -->
- [x] **T011**: Implement `process_webhook_event` in `BillingService` to handle `customer.subscription.updated` and `invoice.payment_succeeded`, updating business entitlements in DB. <!-- id: 10 -->
- [x] **T012**: Add integration tests for webhook processing using simulated Stripe payloads. <!-- id: 11 -->

## WP03: Conversational Tools & State Transitions

- [x] **T013**: Define `GetBillingStatusTool` and `RequestUpgradeTool` in `src/uimodels.py` with Pydantic schemas. <!-- id: 12 -->
- [x] **T014**: Update `ToolExecutor` and `llm_client.py` to register new tools and handle their execution. <!-- id: 13 -->
- [x] **T015**: Implement state transition logic: typing "billing" should move user to `BILLING` state and show status. <!-- id: 14 -->
- [x] **T016**: Update `src/assets/messages.yaml` with templates for billing status, upgrade quotes, and payment links. <!-- id: 15 -->

## WP04: Scope Enforcement

- [ ] **T017**: Add `required_scope: Optional[str]` to `BaseTool` or tool metadata registry. <!-- id: 16 -->
- [ ] **T018**: Implement enforcement logic in `ToolExecutor.execute`: verify `business.active_addons` contains the `required_scope` before running the tool. <!-- id: 17 -->
- [ ] **T019**: Create a `ProServiceTool` (dummy tool) requiring a scope and verify it is blocked for users without the addon in `tests/test_scope_enforcement.py`. <!-- id: 18 -->

## WP05: Usage-Based Billing

- [x] **T020**: Update `Business` model to include `message_count_current_period` (int), `billing_cycle_anchor` (datetime), and `message_credits` (int). <!-- id: 19 -->
- [x] **T021**: Update `BillingService` to support usage tracking: `track_message_sent` decrements credits, reports overage if negative. Reset logic adds 1000 credits/month. <!-- id: 20 -->
- [x] **T022**: Update `get_billing_status` to formatting to include "X credits remaining" or "Overage: Y". <!-- id: 21 -->
- [x] **T023**: Connect `WhatsAppService` (or message sender) to `BillingService.track_message_sent` to increment usage on every outbound message. <!-- id: 22 -->
- [x] **T024**: Verify usage tracking and cost calculation with new tests in `tests/test_usage_billing.py` and `tests/test_billing_fixes.py`. <!-- id: 23 -->
- [x] **T025**: Implement messaging top-up flow and payment handling. <!-- id: 24 -->
