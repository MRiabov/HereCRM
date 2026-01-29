from typing import Dict, Any, Optional
import logging

from src.models import Service
from src.repositories import ServiceRepository
from .syncer_base import AbstractSyncer, QBClientError
from .sync_mappers import validate_required_fields

logger = logging.getLogger(__name__)


class ServiceSyncer(AbstractSyncer):
    """Synchronization logic for Service entities to QuickBooks Items."""

    def __init__(self, db_session, qb_client):
        super().__init__(db_session, qb_client)
        self.service_repo = ServiceRepository(db_session)

    async def _get_record(self, business_id: int, record_id: int) -> Optional[Service]:
        """Get service record from database."""
        return await self.service_repo.get_by_id(record_id, business_id)

    def _map_record(self, service: Service) -> Dict[str, Any]:
        """
        Map Service record to QuickBooks Item (Service type) format.

        Args:
            service: Service database record

        Returns:
            Dict containing QuickBooks Item data
        """
        qb_data = {
            "Name": service.name.strip() if service.name else "",
            "Type": "Service",  # QuickBooks Item type
            "Description": service.description if service.description else "",
        }

        # Unit price - QuickBooks expects this as a string
        if service.default_price is not None:
            qb_data["UnitPrice"] = str(service.default_price)

        return qb_data

    def _validate_record(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Validate service data before sending to QuickBooks.

        Args:
            data: Mapped service data

        Returns:
            Error message if validation fails, None if valid
        """
        # Service name is required for QuickBooks
        return validate_required_fields(data, ["Name"])

    def _push_to_qb(self, qb_client, data: Dict[str, Any]) -> str:
        """
        Push service data to QuickBooks as an Item.

        Args:
            qb_client: QuickBooks API client
            data: Mapped service data

        Returns:
            str: The QuickBooks Item ID
        """
        try:
            # Import here to handle missing quickbooks module gracefully
            from quickbooks.objects.item import Item

            name = data["Name"]

            # Check if item already exists by name
            existing_items = Item.where(f"Name = '{name}'", qb=qb_client)

            if existing_items:
                # Update existing item
                item = existing_items[0]

                # Update fields
                if "Description" in data:
                    item.Description = data["Description"]
                if "UnitPrice" in data:
                    item.UnitPrice = data["UnitPrice"]

                item.save(qb=qb_client)
                logger.info(f"Updated existing QuickBooks item: {item.Id}")
                return str(item.Id)
            else:
                # Create new item
                item = Item()
                item.Name = data["Name"]
                item.Type = data["Type"]

                if "Description" in data:
                    item.Description = data["Description"]
                if "UnitPrice" in data:
                    item.UnitPrice = data["UnitPrice"]

                item.save(qb=qb_client)
                logger.info(f"Created new QuickBooks item: {item.Id}")
                return str(item.Id)

        except ImportError as e:
            logger.error(f"QuickBooks module not available: {str(e)}")
            raise QBClientError(f"QuickBooks module not available: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to push service to QuickBooks: {str(e)}")
            raise QBClientError(f"QuickBooks API error: {str(e)}")
