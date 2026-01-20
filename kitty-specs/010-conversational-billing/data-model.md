# Data Model: Conversational Billing

## Database Schema Changes

### `businesses` Table (Update)

Existing table. New columns to be added via Alembic migration.

| Column Name | Type | Nullable | Default | Description |
|:---|:---|:---|:---|:---|
| `stripe_customer_id` | String | Yes | NULL | Link to Stripe Customer |
| `stripe_subscription_id` | String | Yes | NULL | Link to active subscription |
| `subscription_status` | String | No | 'free' | 'free', 'active', 'past_due', 'canceled' |
| `seat_limit` | Integer | No | 1 | Max allowed users |
| `active_addons` | JSON | No | [] | List of enabled scopes (e.g. `['campaigns', 'employees']`) |

## File Configuration

### `src/config/billing_config.yaml`

Defines the catalog of available upgrades.

```yaml
products:
  seat:
    name: "Additional Seat"
    description: "Add another user to your workspace"
    price_id: "price_H5gg..."  # Stripe Price ID
    unit_amount_decimal: 15.00
    currency: "eur"

addons:
  - id: "employee_management"
    name: "Employee Management"
    description: "Manage shifts and roles"
    price_id: "price_123..."
    scope: "manage_employees"
    price_display: "€10/mo"

  - id: "campaign_messaging"
    name: "Campaign Messaging"
    description: "Bulk messaging tools"
    price_id: "price_456..."
    scope: "campaigns"
    price_display: "€25/mo"
```

## Internal Domain Entities

### `BillingService` Interface

```python
class BillingService:
    async def get_billing_status(self, business_id: int) -> dict:
        """Returns plan, seats, addons."""
        pass

    async def create_checkout_session(self, business_id: int, price_id: str) -> str:
        """Creates a new subscription checkout session. Returns URL."""
        pass

    async def create_upgrade_link(self, business_id: int, item_type: str, item_id: str) -> dict:
        """
        Calculates proration and returns invoice URL.
        Returns: {
            "total_due": float,
            "url": str,
            "description": str
        }
        """
        pass

    async def handle_webhook(self, event_type: str, payload: dict):
        """Processes stripe webhooks."""
        pass
```
