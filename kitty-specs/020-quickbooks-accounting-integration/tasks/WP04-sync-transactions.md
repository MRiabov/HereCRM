---
work_package_id: WP04
title: Sync Logic - Invoices & Payments
lane: "for_review"
dependencies: []
subtasks:
- T015
- T016
- T017
- T018
agent: "Gemini"
shell_pid: "107184"
---

## Objective

Implement synchronization for Invoices and Payments, which is the core value proposition. This involves complex references (Invoice -> Customer, Invoice -> Line Items -> Services, Payment -> Invoice).

## Context

These entities depend on `quickbooks_id`s from the entities synced in WP03. If a dependency is missing (e.g., trying to sync an Invoice for a Customer that failed to sync), we must fail gracefully or skip.

## Detailed Guidance

### Subtask T015: Implement InvoiceSyncer and mapper

**Purpose**: Sync `Invoice` entities.
**Files**: `src/services/accounting/invoice_syncer.py`
**Instructions**:

1. Implement `InvoiceSyncer(AbstractSyncer)`.
2. Pre-flight check: Ensure `invoice.customer.quickbooks_id` exists. If not, raise specific error (or attempt to sync customer JIT - keep it simple: error or return 'skipped'). *Decision*: Raise `DependencyError`.
3. Mapping:
    - `CustomerRef`: `invoice.customer.quickbooks_id`.
    - `TxnDate`: `invoice.date`.
    - `DueDate`: `invoice.due_date`.
    - `Line`: List of line items.
        - For each item: `ItemRef` = `service.quickbooks_id`, `Amount`, `Qty`, `DetailType='SalesItemLineDetail'`.
4. Push logic:
    - Create/Update `Invoice` object.

### Subtask T016: Implement PaymentSyncer and mapper

**Purpose**: Sync `Payment` entities to `Payment` object in QB.
**Files**: `src/services/accounting/payment_syncer.py`
**Instructions**:

1. Implement `PaymentSyncer(AbstractSyncer)`.
2. Pre-flight: Ensure `payment.invoice.quickbooks_id` AND `payment.invoice.customer.quickbooks_id` exist.
3. Mapping:
    - `CustomerRef`: `payment.invoice.customer.quickbooks_id`.
    - `TotalAmt`: `payment.amount`.
    - `TxnDate`: `payment.date`.
    - `Line`: Link to invoice.
        - `Amount`: `payment.amount`.
        - `LinkedTxn`: `[{'TxnId': payment.invoice.quickbooks_id, 'TxnType': 'Invoice'}]`.
4. Push logic: Create `Payment`.

### Subtask T017: Implement linked transaction logic

**Purpose**: Ensure robust handling of dependencies.
**Files**: `src/services/accounting/utils.py` or modify Syncers.
**Instructions**:

1. In `InvoiceSyncer` & `PaymentSyncer`: verify `DependencyError` is caught and logged distinctively (Status: 'failed', Error: "Dependency missing: Customer not synced").
2. This allows the orchestrator (next WP) to know why it failed.

### Subtask T018: Add unit tests for Invoice and Payment sync logic

**Purpose**: Verify complex mapping and dependency handling.
**Files**: `tests/unit/test_sync_transactions.py`
**Instructions**:

1. Test `InvoiceSyncer` matches Line Items correctly.
2. Test `PaymentSyncer` links to Invoice correctly.
3. Test rejection if `Customer.quickbooks_id` is None.

## Definition of Done

- Invoices and Payments can be mapped and pushed.
- Dependencies are strictly enforced (no push if referenced ID is missing).
- Tests pass.

## Verification

- Run `pytest tests/unit/test_sync_transactions.py`.

## Activity Log

- 2026-01-22T09:59:29Z – Gemini – shell_pid=107184 – lane=doing – Started implementation via workflow command
- 2026-01-22T10:12:24Z – Gemini – shell_pid=107184 – lane=for_review – Ready for review: Implemented InvoiceSyncer and PaymentSyncer with robust dependency handling and comprehensive unit tests.
