from typing import Dict, Any, Optional
import logging
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import Payment, Invoice, Job
from .syncer_base import AbstractSyncer, QBClientError, DependencyError
from .sync_mappers import validate_required_fields

logger = logging.getLogger(__name__)


class PaymentSyncer(AbstractSyncer):
    """Synchronization logic for Payment entities to QuickBooks."""

    async def _get_record(self, business_id: int, record_id: int) -> Optional[Payment]:
        """
        Get payment record from database with all necessary relationships.
        """
        stmt = (
            select(Payment)
            .options(
                joinedload(Payment.invoice)
                .joinedload(Invoice.job)
                .joinedload(Job.customer)
            )
            .where(Payment.id == record_id)
        )
        result = await self.db_session.execute(stmt)
        payment = result.unique().scalar_one_or_none()

        # Verify it belongs to the business
        if (
            payment
            and payment.invoice
            and payment.invoice.job
            and payment.invoice.job.business_id != business_id
        ):
            return None

        return payment

    def _map_record(self, payment: Payment) -> Dict[str, Any]:
        """
        Map Payment record to QuickBooks Payment format.
        """
        invoice = payment.invoice
        if not invoice:
            raise ValueError(f"Payment {payment.id} has no associated invoice.")

        if not invoice.quickbooks_id:
            raise DependencyError(f"Invoice {invoice.id} is not synced to QuickBooks.")

        job = invoice.job
        if not job or not job.customer:
            raise ValueError(
                f"Invoice {invoice.id} has no associated customer via job."
            )

        customer = job.customer
        if not customer.quickbooks_id:
            raise DependencyError(
                f"Customer {customer.id} is not synced to QuickBooks."
            )

        # Mapping:
        # CustomerRef: payment.invoice.customer.quickbooks_id.
        # TotalAmt: payment.amount.
        # TxnDate: payment.date.
        # Line: Link to invoice.
        # Amount: payment.amount.
        # LinkedTxn: [{'TxnId': payment.invoice.quickbooks_id, 'TxnType': 'Invoice'}].

        qb_data = {
            "CustomerRef": {"value": customer.quickbooks_id},
            "TotalAmt": payment.amount,
            "TxnDate": payment.payment_date.date().isoformat()
            if payment.payment_date
            else None,
            "Line": [
                {
                    "Amount": payment.amount,
                    "LinkedTxn": [
                        {"TxnId": invoice.quickbooks_id, "TxnType": "Invoice"}
                    ],
                }
            ],
        }

        # Preserve QB ID if we have it
        if hasattr(payment, "quickbooks_id") and payment.quickbooks_id:
            qb_data["Id"] = payment.quickbooks_id

        return qb_data

    def _validate_record(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Validate payment data before sending to QuickBooks.
        """
        error = validate_required_fields(data, ["CustomerRef", "TotalAmt"])
        if error:
            return error

        if not data.get("Line"):
            return "Payment must be linked to at least one transaction (Invoice)."

        return None

    def _push_to_qb(self, qb_client, data: Dict[str, Any]) -> str:
        """
        Push payment data to QuickBooks.
        """
        try:
            from quickbooks.objects.payment import Payment as QBPayment
            from quickbooks.objects.payment import PaymentLine, LinkedTxn

            qb_payment = None

            # 1. Try fetching by ID if available
            if "Id" in data and data["Id"]:
                try:
                    qb_payment = QBPayment.get(data["Id"], qb=qb_client)
                    logger.info(
                        f"Found existing QuickBooks payment by ID: {data['Id']}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not fetch payment by ID {data['Id']}: {str(e)}"
                    )

            # 2. Create new if not found
            if not qb_payment:
                qb_payment = QBPayment()
                logger.info("Creating new QuickBooks payment")

            # Update fields
            qb_payment.CustomerRef = data["CustomerRef"]
            qb_payment.TotalAmt = data["TotalAmt"]
            if data.get("TxnDate"):
                qb_payment.TxnDate = data["TxnDate"]

            # Handle Lines
            qb_lines = []
            for line_data in data["Line"]:
                line = PaymentLine()
                line.Amount = line_data["Amount"]

                linked_txns = []
                for txn_data in line_data["LinkedTxn"]:
                    linked_txn = LinkedTxn()
                    linked_txn.TxnId = txn_data["TxnId"]
                    linked_txn.TxnType = txn_data["TxnType"]
                    linked_txns.append(linked_txn)

                line.LinkedTxn = linked_txns
                qb_lines.append(line)

            qb_payment.Line = qb_lines

            qb_payment.save(qb=qb_client)
            return str(qb_payment.Id)

        except ImportError as e:
            logger.error(f"QuickBooks module not available: {str(e)}")
            raise QBClientError(f"QuickBooks module not available: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to push payment to QuickBooks: {str(e)}")
            raise QBClientError(f"QuickBooks API error: {str(e)}")
