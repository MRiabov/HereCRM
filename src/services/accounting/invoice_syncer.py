from typing import Dict, Any, Optional
import logging
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.models import Invoice, Job, LineItem
from .syncer_base import AbstractSyncer, QBClientError, DependencyError
from .sync_mappers import validate_required_fields

logger = logging.getLogger(__name__)


class InvoiceSyncer(AbstractSyncer):
    """Synchronization logic for Invoice entities to QuickBooks."""

    async def _get_record(self, business_id: int, record_id: int) -> Optional[Invoice]:
        """
        Get invoice record from database with all necessary relationships.
        """
        stmt = (
            select(Invoice)
            .options(
                joinedload(Invoice.job).joinedload(Job.customer),
                joinedload(Invoice.job)
                .joinedload(Job.line_items)
                .joinedload(LineItem.service),
            )
            .where(Invoice.id == record_id)
        )
        result = await self.db_session.execute(stmt)
        invoice = result.unique().scalar_one_or_none()

        # Verify it belongs to the business
        if invoice and invoice.job and invoice.job.business_id != business_id:
            return None

        return invoice

    def _map_record(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Map Invoice record to QuickBooks Invoice format.
        """
        job = invoice.job
        if not job:
            raise ValueError(f"Invoice {invoice.id} has no associated job.")

        customer = job.customer
        if not customer:
            raise ValueError(f"Job {job.id} has no associated customer.")

        if not customer.quickbooks_id:
            raise DependencyError(
                f"Customer {customer.id} is not synced to QuickBooks."
            )

        # Basic invoice info
        qb_data = {
            "CustomerRef": {"value": customer.quickbooks_id},
            "TxnDate": invoice.created_at.date().isoformat()
            if invoice.created_at
            else None,
            "Line": [],
        }

        # Map Line Items
        for item in job.line_items:
            line = {
                "Amount": item.total_price,
                "Description": item.description,
                "DetailType": "SalesItemLineDetail",
                "SalesItemLineDetail": {
                    "Qty": item.quantity,
                    "UnitPrice": item.unit_price,
                },
            }

            # Add Service Reference if available and synced
            if item.service:
                if not item.service.quickbooks_id:
                    # In a real scenario, we might want to sync the service JIT
                    # But per instructions, we fail gracefully or skip.
                    raise DependencyError(
                        f"Service {item.service.id} ({item.service.name}) is not synced to QuickBooks."
                    )

                line["SalesItemLineDetail"]["ItemRef"] = {
                    "value": item.service.quickbooks_id
                }

            qb_data["Line"].append(line)

        # Preserve QB ID if we have it
        if hasattr(invoice, "quickbooks_id") and invoice.quickbooks_id:
            qb_data["Id"] = invoice.quickbooks_id

        return qb_data

    def _validate_record(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Validate invoice data before sending to QuickBooks.
        """
        error = validate_required_fields(data, ["CustomerRef"])
        if error:
            return error

        if not data.get("Line"):
            return "Invoice must have at least one line item."

        return None

    def _push_to_qb(self, qb_client, data: Dict[str, Any]) -> str:
        """
        Push invoice data to QuickBooks.
        """
        try:
            from quickbooks.objects.invoice import Invoice as QBInvoice

            qb_invoice = None

            # 1. Try fetching by ID if available
            if "Id" in data and data["Id"]:
                try:
                    qb_invoice = QBInvoice.get(data["Id"], qb=qb_client)
                    logger.info(
                        f"Found existing QuickBooks invoice by ID: {data['Id']}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not fetch invoice by ID {data['Id']}: {str(e)}"
                    )

            # 2. Create new if not found
            if not qb_invoice:
                qb_invoice = QBInvoice()
                logger.info("Creating new QuickBooks invoice")

            # Update fields
            qb_invoice.CustomerRef = data["CustomerRef"]
            if data.get("TxnDate"):
                qb_invoice.TxnDate = data["TxnDate"]

            # Handle Line Items
            # Note: The quickbooks-python library might require special handling for Lines
            from quickbooks.objects.invoice import InvoiceLine, SalesItemLineDetail

            qb_lines = []
            for line_data in data["Line"]:
                line = InvoiceLine()
                line.Amount = line_data["Amount"]
                line.Description = line_data["Description"]
                line.DetailType = line_data["DetailType"]

                detail = SalesItemLineDetail()
                detail.Qty = line_data["SalesItemLineDetail"]["Qty"]
                detail.UnitPrice = line_data["SalesItemLineDetail"]["UnitPrice"]

                if "ItemRef" in line_data["SalesItemLineDetail"]:
                    detail.ItemRef = line_data["SalesItemLineDetail"]["ItemRef"]

                line.SalesItemLineDetail = detail
                qb_lines.append(line)

            qb_invoice.Line = qb_lines

            qb_invoice.save(qb=qb_client)
            return str(qb_invoice.Id)

        except ImportError as e:
            logger.error(f"QuickBooks module not available: {str(e)}")
            raise QBClientError(f"QuickBooks module not available: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to push invoice to QuickBooks: {str(e)}")
            raise QBClientError(f"QuickBooks API error: {str(e)}")
