# Quickstart: Conversational Billing

## Environment Setup

To run the billing features locally, you need Stripe API keys.

1. **Get Keys**: Sign up for Stripe (Test Mode).
2. **Env Vars**: Add to `.env`:

   ```bash
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

## Configuration

Ensure `src/config/billing_config.yaml` exists. A default one is created by the implementation tasks, but for testing you can use:

```yaml
products:
  seat:
    name: "Seat"
    price_id: "price_test_seat"
addons:
  - id: "campaigns"
    name: "Campaigns"
    price_id: "price_test_campaign"
    scope: "campaigns"
```

## Testing

### Manual Testing (Chat)

1. **View Status**: Send "billing" or "settings" -> "billing".
2. **Upgrade**: Send "add seat" or "add campaigns".
   - *Expected*: Bot replies with a Stripe URL (Test Mode).
   - *Action*: Click link, fill dummy card (4242...), pay.
3. **Verify**: Send "billing" again. Status should update (after webhook).

### Webhook Simulation

Use the Stripe CLI to forward webhooks:

```bash
stripe listen --forward-to localhost:8000/api/webhooks/stripe
```

### Unit Tests

Run the billing suite:

```bash
pytest src/tests/test_billing_service.py
```
