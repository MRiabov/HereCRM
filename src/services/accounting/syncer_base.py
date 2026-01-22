from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import logging
import asyncio

logger = logging.getLogger(__name__)


class QBClientError(Exception):
    """Custom exception for QuickBooks API errors."""
    pass


class DependencyError(Exception):
    """Raised when a dependency (like Customer or Service) is not yet synced."""
    pass


class AbstractSyncer(ABC):
    """Base class for QuickBooks synchronization logic."""
    
    def __init__(self, db_session, qb_client):
        """
        Initialize the syncer.
        
        Args:
            db_session: Database session for updating records
            qb_client: QuickBooks API client instance
        """
        self.db_session = db_session
        self.qb_client = qb_client
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def sync(self, business_id: int, record_id: int) -> bool:
        """
        Main synchronization method.
        
        Args:
            business_id: The business ID
            record_id: The record ID to sync
            
        Returns:
            bool: True if sync was successful, False otherwise
        """
        record = await self._get_record(business_id, record_id)
        if not record:
            self.logger.error(f"Record not found: business_id={business_id}, record_id={record_id}")
            return False
            
        try:
            # Map the record to QuickBooks format
            qb_data = self._map_record(record)
            
            # Validate mapped data
            validation_error = self._validate_record(qb_data)
            if validation_error:
                await self._update_status(record, 'failed', error=validation_error)
                return False
            
            # Push to QuickBooks - Use to_thread as _push_to_qb is synchronous and does network I/O
            qb_id = await asyncio.to_thread(self._push_to_qb, self.qb_client, qb_data)
            
            # Update status on success
            await self._update_status(record, 'synced', qb_id=qb_id)
            self.logger.info(f"Successfully synced record {record_id} to QuickBooks ID {qb_id}")
            return True
            
        except DependencyError as e:
            self.logger.warning(f"Dependency missing for record {record_id}: {e}")
            await self._update_status(record, 'failed', error=str(e))
            return False
        except QBClientError as e:
            self.logger.error(f"QuickBooks API error syncing record {record_id}: {str(e)}")
            await self._update_status(record, 'failed', error=str(e))
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error syncing record {record_id}: {str(e)}", exc_info=True)
            await self._update_status(record, 'failed', error=str(e))
            return False
    
    @abstractmethod
    async def _get_record(self, business_id: int, record_id: int):
        """Get the record from database. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _map_record(self, record) -> Dict[str, Any]:
        """
        Map the record to QuickBooks API format.
        Must be implemented by subclasses.
        
        Args:
            record: The database record
            
        Returns:
            Dict containing QuickBooks-compatible data
        """
        pass
    
    @abstractmethod
    def _push_to_qb(self, qb_client, data: Dict[str, Any]) -> str:
        """
        Push the mapped data to QuickBooks API.
        Must be implemented by subclasses.
        
        Args:
            qb_client: QuickBooks API client
            data: Mapped data in QuickBooks format
            
        Returns:
            str: The QuickBooks ID of the created/updated record
        """
        pass
    
    def _validate_record(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Validate the mapped data before sending to QuickBooks.
        Can be overridden by subclasses for specific validation.
        
        Args:
            data: Mapped data
            
        Returns:
            Optional[str]: Error message if validation fails, None if valid
        """
        return None
    
    async def _update_status(self, record, status: str, qb_id: Optional[str] = None, error: Optional[str] = None):
        """
        Update the sync status of a record.
        
        Args:
            record: The database record to update
            status: The sync status ('synced', 'failed', 'pending')
            qb_id: The QuickBooks ID (if sync was successful)
            error: Error message (if sync failed)
        """
        try:
            # Update sync status fields
            if hasattr(record, 'quickbooks_sync_status'):
                record.quickbooks_sync_status = status
            elif hasattr(record, 'sync_status'): # Support both naming conventions if needed
                record.sync_status = status
                
            if hasattr(record, 'quickbooks_id') and qb_id:
                record.quickbooks_id = qb_id
                
            if hasattr(record, 'quickbooks_sync_error'):
                record.quickbooks_sync_error = error
            elif hasattr(record, 'sync_error'):
                record.sync_error = error
                
            if hasattr(record, 'quickbooks_synced_at') and status == 'synced':
                record.quickbooks_synced_at = datetime.now(timezone.utc)
            elif hasattr(record, 'synced_at') and status == 'synced':
                record.synced_at = datetime.now(timezone.utc)
            
            # Commit the changes
            await self.db_session.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to update sync status for record {record.id}: {str(e)}")
            await self.db_session.rollback()
            raise