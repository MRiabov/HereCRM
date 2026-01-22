import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.models import Business, Customer, Service, SyncLog, SyncLogStatus, SyncType, QuickBooksSyncStatus
from src.services.accounting.quickbooks_sync import QuickBooksSyncManager

@pytest.mark.asyncio
async def test_full_sync_cycle(async_session):
    """Test a successful synchronization cycle for all entities."""
    # 1. Setup Data
    business = Business(
        name="Test Business",
        quickbooks_connected=True,
        quickbooks_realm_id="12345",
        quickbooks_access_token="access",
        quickbooks_refresh_token="refresh",
        quickbooks_token_expiry=datetime.now(timezone.utc).replace(year=2030)
    )
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer = Customer(
        name="Test Customer",
        business_id=business.id,
        quickbooks_sync_status=QuickBooksSyncStatus.PENDING
    )
    service = Service(
        name="Test Service",
        business_id=business.id,
        default_price=100.0,
        quickbooks_sync_status=QuickBooksSyncStatus.PENDING
    )
    async_session.add_all([customer, service])
    await async_session.commit()

    # 2. Mock QuickBooks Client and Syncers
    with patch("src.services.accounting.quickbooks_sync.QuickBooks") as mock_qb_class:
        mock_qb_client = MagicMock()
        mock_qb_class.return_value = mock_qb_client
        
        # Mock the syncer's _push_to_qb to avoid actual API calls
        with patch("src.services.accounting.customer_syncer.CustomerSyncer._push_to_qb", return_value="QB_CUST_123"):
            with patch("src.services.accounting.service_syncer.ServiceSyncer._push_to_qb", return_value="QB_SRV_456"):
                
                # 3. Run Sync
                manager = QuickBooksSyncManager(async_session)
                sync_log = await manager.run_sync(business.id, SyncType.MANUAL)

                # 4. Verify Results
                assert sync_log.status == SyncLogStatus.SUCCESS
                assert sync_log.records_processed == 2
                assert sync_log.records_succeeded == 2
                assert sync_log.records_failed == 0

                # Verify records updated
                await async_session.refresh(customer)
                await async_session.refresh(service)
                assert customer.quickbooks_id == "QB_CUST_123"
                assert customer.quickbooks_sync_status == QuickBooksSyncStatus.SYNCED
                assert service.quickbooks_id == "QB_SRV_456"
                assert service.quickbooks_sync_status == QuickBooksSyncStatus.SYNCED

                # Verify business updated
                await async_session.refresh(business)
                assert business.quickbooks_last_sync is not None

@pytest.mark.asyncio
async def test_sync_partial_failure(async_session):
    """Test that sync continues even if some records fail."""
    # Setup
    business = Business(
        name="Test Biz", 
        quickbooks_connected=True,
        quickbooks_token_expiry=datetime.now(timezone.utc).replace(year=2030)
    )
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    customer1 = Customer(name="Good Cust", business_id=business.id, quickbooks_sync_status=QuickBooksSyncStatus.PENDING)
    customer2 = Customer(name="Bad Cust", business_id=business.id, quickbooks_sync_status=QuickBooksSyncStatus.PENDING)
    async_session.add_all([customer1, customer2])
    await async_session.commit()

    with patch("src.services.accounting.quickbooks_sync.QuickBooks"):
        # Mock success for first, failure for second
        # Note: We patch the base class _push_to_qb to simulate API error
        with patch("src.services.accounting.customer_syncer.CustomerSyncer._push_to_qb") as mock_push:
            mock_push.side_effect = ["QB_OK", Exception("QB API Error")]
            
            manager = QuickBooksSyncManager(async_session)
            sync_log = await manager.run_sync(business.id)

            assert sync_log.status == SyncLogStatus.PARTIAL_SUCCESS
            assert sync_log.records_processed == 2
            assert sync_log.records_succeeded == 1
            assert sync_log.records_failed == 1
            
            # Verify error details logged
            assert sync_log.error_details is not None
            assert any("QB API Error" in str(err) for err in sync_log.error_details.get("errors", []))

@pytest.mark.asyncio
async def test_sync_not_connected(async_session):
    """Test that sync fails if QuickBooks is not connected."""
    business = Business(name="Unconnected Biz", quickbooks_connected=False)
    async_session.add(business)
    await async_session.commit()
    await async_session.refresh(business)

    manager = QuickBooksSyncManager(async_session)
    sync_log = await manager.run_sync(business.id)

    assert sync_log.status == SyncLogStatus.FAILED
    assert "not connected" in sync_log.error_details.get("error", "").lower()
