# Data Model - Clerk Authentication

## Entities

### User (Modifications)

Extends existing `User` model.

| Field | Type | Description |
| :--- | :--- | :--- |
| `clerk_id` | String (Unique, Nullable) | The Clerk User ID (`user_...`). Used for authentication mapping. |

### Business (Modifications)

Extends existing `Business` model.

| Field | Type | Description |
| :--- | :--- | :--- |
| `clerk_org_id` | String (Unique, Nullable) | The Clerk Organization ID (`org_...`). Used for tenant mapping. |

## Relationships

- `User` belongs to `Business` (Existing).
- **Constraint**: `User.business.clerk_org_id` MUST match the Organization ID in the Clerk Session Token.

## Webhook Payloads

We consume the following Clerk events to sync data.

### `user.created` / `user.updated`

```json
{
  "data": {
    "id": "user_123",
    "email_addresses": [{"email_address": "alice@example.com"}],
    "phone_numbers": [{"phone_number": "+15551234567"}]
  },
  "type": "user.created"
}
```

### `organization.created` / `organization.updated`

```json
{
  "data": {
    "id": "org_456",
    "name": "Alice's Bakery"
  },
  "type": "organization.created"
}
```
