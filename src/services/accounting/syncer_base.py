from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

# Assuming some database session management is available, likely passed in constructor or context
# For now, I'll keep it generic.

class DependencyError(Exception):
    """Raised when a dependency (like Customer or Service) is not yet synced."""
    pass

class AbstractSyncer(ABC):
    def __init__(self, db_session, qb_client):
        self.db = db_session
        self.qb_client = qb_client
        self.logger = logging.getLogger(self.__class__.__name__)

    def sync(self, business_id: int, record_id: int):
        """
        Main entry point to sync a record.
        """
        record = self._fetch_record(record_id)
        if not record:
            self.logger.error(f"Record {record_id} not found.")
            return

        try:
            data = self._map_record(record)
            qb_id = self._push_to_qb(self.qb_client, data)
            self._update_status(record, 'synced', qb_id=qb_id)
            self.logger.info(f"Successfully synced record {record_id} to QB ID {qb_id}")
        except DependencyError as e:
            self.logger.warning(f"Dependency missing for record {record_id}: {e}")
            self._update_status(record, 'failed', error=str(e))
        except Exception as e:
            self.logger.error(f"Failed to sync record {record_id}: {e}", exc_info=True)
            self._update_status(record, 'failed', error=str(e))

    @abstractmethod
    def _fetch_record(self, record_id: int) -> Any:
        """Fetch the record from DB."""
        pass

    @abstractmethod
    def _map_record(self, record: Any) -> Dict[str, Any]:
        """Map DB record to QB dict."""
        pass

    @abstractmethod
    def _push_to_qb(self, qb_client, data: Dict[str, Any]) -> str:
        """Push data to QB and return QB ID."""
        pass

    def _update_status(self, record: Any, status: str, qb_id: Optional[str] = None, error: Optional[str] = None):
        """Update the sync status of the record."""
        # This assumes the record is an SQLAlchemy model instance attached to self.db
        if hasattr(record, 'quickbooks_sync_status'):
            record.quickbooks_sync_status = status
        
        if qb_id and hasattr(record, 'quickbooks_id'):
            record.quickbooks_id = qb_id
        
        if error and hasattr(record, 'sync_error'):
            record.sync_error = error
        
        self.db.commit()
