import logging
import time
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from quickbooks import QuickBooks

from src.models import (
    Business,
    Customer,
    Service,
    Invoice,
    SyncLog,
    SyncLogStatus,
    SyncType,
    QuickBooksSyncStatus,
)
from .customer_syncer import CustomerSyncer
from .service_syncer import ServiceSyncer

logger = logging.getLogger(__name__)


class QuickBooksSyncManager:
    """Orchestrates the synchronization of data between HereCRM and QuickBooks."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client_id = os.getenv("QUICKBOOKS_CLIENT_ID")
        self.client_secret = os.getenv("QUICKBOOKS_CLIENT_SECRET")
        self.environment = os.getenv("QUICKBOOKS_ENVIRONMENT", "sandbox")

    async def run_sync(
        self, business_id: int, sync_type: SyncType = SyncType.SCHEDULED
    ) -> SyncLog:
        """
        Runs a full synchronization for a specific business.

        Order of sync:
        1. Customers
        2. Services
        3. Invoices (WP04)
        4. Payments (WP04)
        """
        start_time = time.time()

        # 1. Create SyncLog
        sync_log = SyncLog(
            business_id=business_id,
            sync_type=sync_type,
            status=SyncLogStatus.PROCESSING,
            sync_timestamp=datetime.now(timezone.utc),
        )
        self.db.add(sync_log)
        await self.db.commit()
        await self.db.refresh(sync_log)

        try:
            # 2. Authenticate & Get Client
            stmt = select(Business).where(Business.id == business_id)
            result = await self.db.execute(stmt)
            business = result.scalar_one_or_none()

            if not business or not business.quickbooks_connected:
                raise ValueError(
                    f"Business {business_id} is not connected to QuickBooks"
                )

            # Handle token refresh if needed
            qb_client = await self._get_qb_client(business)

            # 3. Perform Sync by entity type
            stats = {
                "customers": {"processed": 0, "succeeded": 0, "FAILED": 0},
                "services": {"processed": 0, "succeeded": 0, "FAILED": 0},
                "invoices": {"processed": 0, "succeeded": 0, "FAILED": 0},
            }

            errors = []

            # --- Sync Customers ---
            customers_to_sync = await self._get_pending_records(Customer, business_id)
            stats["customers"]["processed"] = len(customers_to_sync)
            customer_syncer = CustomerSyncer(self.db, qb_client)
            for customer in customers_to_sync:
                success = await customer_syncer.sync(business_id, customer.id)
                if success:
                    stats["customers"]["succeeded"] += 1
                else:
                    stats["customers"]["FAILED"] += 1
                    if len(errors) < 5:
                        errors.append(
                            f"Customer {customer.id}: {customer.quickbooks_sync_error}"
                        )

            # --- Sync Services ---
            services_to_sync = await self._get_pending_records(Service, business_id)
            stats["services"]["processed"] = len(services_to_sync)
            service_syncer = ServiceSyncer(self.db, qb_client)
            for service in services_to_sync:
                success = await service_syncer.sync(business_id, service.id)
                if success:
                    stats["services"]["succeeded"] += 1
                else:
                    stats["services"]["FAILED"] += 1
                    if len(errors) < 5:
                        errors.append(
                            f"Service {service.id}: {service.quickbooks_sync_error}"
                        )

            # --- Sync Invoices (Placeholder for WP04) ---
            # In WP04, InvoiceSyncer will be added here
            invoices_to_sync = await self._get_pending_records(Invoice, business_id)
            stats["invoices"]["processed"] = len(invoices_to_sync)
            # if stats["invoices"]["processed"] > 0:
            #     logger.info(f"Skipping {len(invoices_to_sync)} invoices (WP04 placeholder)")

            # 4. Finalize SyncLog
            duration = time.time() - start_time
            sync_log.records_processed = sum(s["processed"] for s in stats.values())
            sync_log.records_succeeded = sum(s["succeeded"] for s in stats.values())
            sync_log.records_failed = sum(s["FAILED"] for s in stats.values())
            sync_log.duration_seconds = duration
            sync_log.error_details = {"errors": errors} if errors else None

            if sync_log.records_failed == 0:
                sync_log.status = SyncLogStatus.SUCCESS
            elif sync_log.records_succeeded > 0:
                sync_log.status = SyncLogStatus.PARTIAL_SUCCESS
            else:
                sync_log.status = SyncLogStatus.FAILED

            business.quickbooks_last_sync = datetime.now(timezone.utc)
            await self.db.commit()

            return sync_log

        except Exception as e:
            logger.error(f"Sync failed for business {business_id}: {str(e)}")
            sync_log.status = SyncLogStatus.FAILED
            sync_log.error_details = {"error": str(e)}
            await self.db.commit()
            return sync_log

    async def _get_pending_records(self, model, business_id: int):
        if model == Invoice:
            from src.models import Job

            stmt = (
                select(Invoice)
                .join(Job)
                .where(
                    and_(
                        Job.business_id == business_id,
                        Invoice.quickbooks_sync_status != QuickBooksSyncStatus.SYNCED,
                    )
                )
            )
        else:
            stmt = select(model).where(
                and_(
                    model.business_id == business_id,
                    model.quickbooks_sync_status != QuickBooksSyncStatus.SYNCED,
                )
            )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def _get_qb_client(self, business: Business) -> QuickBooks:
        """Initialize and return a QuickBooks client, refreshing tokens if necessary."""
        # Check if tokens need refresh (5 minute buffer)
        now = datetime.now(timezone.utc)
        expiry = business.quickbooks_token_expiry
        if expiry:
            # Ensure expiry is timezone-aware for comparison
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            if expiry < now + timedelta(minutes=5):
                await self._refresh_tokens(business)

        return QuickBooks(
            auth_client=None,  # In real app, would use an auth client wrapper
            client_id=self.client_id,
            client_secret=self.client_secret,
            access_token=business.quickbooks_access_token,
            refresh_token=business.quickbooks_refresh_token,
            company_id=business.quickbooks_realm_id,
            environment=self.environment,
        )

    async def _refresh_tokens(self, business: Business):
        """Refreshes QuickBooks OAuth tokens."""
        # This is a simplified version. In a real app, you'd use the AuthClient from SDK.
        logger.info(f"Refreshing QuickBooks tokens for business {business.id}")
        # Placeholder for real refresh logic from WP02
        # For now, we'll assume the client handles it or it's done elsewhere
        pass

    async def trigger_manual_sync(self, business_id: int):
        """Trigger a manual sync in the background."""
        # This would be called from a tool/API
        # We'll run it and return the log
        return await self.run_sync(business_id, sync_type=SyncType.MANUAL)
