# Data Model: Business Workflow Defaults

Path: kitty-specs/019-business-workflow-defaults/data-model.md

## Entity: Business (Updated)

We will add flattened columns to the `Business` table to store workflow settings. This ensures type safety and easier querying.

| Field | Type | Description | Default |
|:------|:-----|:------------|:--------|
| `workflow_invoicing` | SQL Enum | `never`, `manual`, `automatic` | `manual` |
| `workflow_quoting` | SQL Enum | `never`, `manual`, `automatic` | `manual` |
| `workflow_payment_timing` | SQL Enum | `always_paid_on_spot`, `usually_paid_on_spot`, `paid_later` | `usually_paid_on_spot` |
| `workflow_tax_inclusive` | Boolean | Whether prices include tax | `True` |
| `workflow_include_payment_terms` | Boolean | Whether to show net terms on invoices | `False` |
| `workflow_enable_reminders` | Boolean | Whether to send auto-reminders | `False` |

### Enums

#### InvoicingWorkflow

- `NEVER`: "never"
- `MANUAL`: "manual"
- `AUTOMATIC`: "automatic"

#### QuotingWorkflow

- `NEVER`: "never"
- `MANUAL`: "manual"
- `AUTOMATIC`: "automatic"

#### PaymentTiming

- `ALWAYS_PAID_ON_SPOT`: "always_paid_on_spot"
- `USUALLY_PAID_ON_SPOT`: "usually_paid_on_spot"
- `PAID_LATER`: "paid_later"

## Logic Enforcements

1. **Job Creation**: If `payment_timing == "always_paid_on_spot"`, then `Job.paid = true`.
2. **Tool Execution**:
   - `SendInvoiceTool`: Disabled if `invoicing == "never"`.
   - `SendQuoteTool`: Disabled if `quoting == "never"`.
   - Payment Tools: Disabled if `payment_timing == "always_paid_on_spot"`.
3. **Permissions**: Only `OWNER` role can modify `workflow` settings.
