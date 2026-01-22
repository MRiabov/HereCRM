# API Contract: Settings Management

Path: kitty-specs/019-business-workflow-defaults/contracts/settings.md

## Tool: UpdateWorkflowSettings

Updates the workflow configuration for the current business.

### Parameters

- `invoicing` (Optional[str]): "never", "manual", or "automatic"
- `quoting` (Optional[str]): "never", "manual", or "automatic"
- `payment_timing` (Optional[str]): "always_paid_on_spot", "usually_paid_on_spot", or "paid_later"
- `tax_inclusive` (Optional[bool]): Whether prices include tax
- `include_payment_terms` (Optional[bool]): Whether to show net terms on invoices
- `enable_reminders` (Optional[bool]): Whether to send auto-reminders

### Validation

- Must be called by a user with `OWNER` role.
- Input values must match the allowed enums.

### Response

- **Success**: Status message confirming the change.
- **Error**: Permission denied or invalid parameter error.

---

## Tool: GetWorkflowSettings

Retrieves the current workflow configuration.

### Response

- A JSON object containing the current workflow state.
