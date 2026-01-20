# Tasks: Conversational Billing & Addons

## WP00: Foundation & Data Model

- [ ] **T001**: Install `stripe` python package and add to `pyproject.toml`. <!-- id: 0 -->
- [ ] **T002**: Create `src/config/billing_config.yaml` with sample products (Seats, Addons). <!-- id: 1 -->
- [ ] **T003**: Generate Alembic migration to add `stripe_customer_id`, `subscription_status`, `seat_limit`, `active_addons` to `businesses` table. <!-- id: 2 -->
- [ ] **T004**: Update `Business` SQLAlchemy model and `BusinessRepository` to support new fields. <!-- id: 3 -->

## WP01: Billing Service Logic

- [ ] **T005**: Create `src/services/billing_service.py` skeleton and `BillingService` class. <!-- id: 4 -->
- [ ] **T006**: Implement `get_billing_status(business_id)` returning formatted status. <!-- id: 5 -->
- [ ] **T007**: Implement `create_checkout_session` (for initial/new subs) and `create_upgrade_link` (modify sub -> get invoice URL). <!-- id: 6 -->
- [ ] **T008**: Add `tests/test_billing_service.py` with mocked Stripe responses for all methods. <!-- id: 7 -->

## WP02: Webhook Handling

- [ ] **T009**: Create `src/api/webhooks/stripe_webhook.py` endpoint to receive events. <!-- id: 8 -->
- [ ] **T010**: Implement `process_webhook_event` in `BillingService` to handle `customer.subscription.updated` and `invoice.payment_succeeded`. Sync `active_addons` and `seat_limit`. <!-- id: 9 -->
- [ ] **T011**: Add integration tests for webhook processing (simulating Stripe payload). <!-- id: 10 -->

## WP03: Conversational Tools

- [ ] **T012**: Define `GetBillingStatusTool` and `RequestUpgradeTool` in `src/uimodels.py`. <!-- id: 11 -->
- [ ] **T013**: Handle new tools in `ToolExecutor`. `RequestUpgradeTool` should call service to generate link and return it. <!-- id: 12 -->
- [ ] **T014**: Update `CRMService` or `ChatUtils` to render the Billing Status template. <!-- id: 13 -->

## WP04: Scope Enforcement

- [ ] **T015**: Add `required_scope` attribute to `BaseTool` (or handle in Executor map). <!-- id: 14 -->
- [ ] **T016**: Implement enforcement logic in `ToolExecutor.execute`: Check `business.active_addons` against tool scope. <!-- id: 15 -->
- [ ] **T017**: Create a dummy "Pro Tool" (e.g. `MassEmailTool`) requiring a scope, and verify it is blocked for free users in tests. <!-- id: 16 -->
