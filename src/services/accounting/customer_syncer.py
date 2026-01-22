from typing import Dict, Any, Optional
import logging

from src.models import Customer
from src.repositories import CustomerRepository
from .syncer_base import AbstractSyncer, QBClientError
from .sync_mappers import map_address_to_qb, validate_required_fields, clean_phone_number

logger = logging.getLogger(__name__)


class CustomerSyncer(AbstractSyncer):
    """Synchronization logic for Customer entities to QuickBooks."""
    
    def __init__(self, db_session, qb_client):
        super().__init__(db_session, qb_client)
        self.customer_repo = CustomerRepository(db_session)
    
    async def _get_record(self, business_id: int, record_id: int) -> Optional[Customer]:
        """Get customer record from database."""
        return await self.customer_repo.get_by_id(record_id, business_id)
    
    def _map_record(self, customer: Customer) -> Dict[str, Any]:
        """
        Map Customer record to QuickBooks Customer format.
        
        Args:
            customer: Customer database record
            
        Returns:
            Dict containing QuickBooks Customer data
        """
        # Basic customer info
        qb_data = {
            'DisplayName': customer.name.strip() if customer.name else '',
            'Notes': customer.details if customer.details else None,
        }
        
        # Phone number
        if customer.phone:
            cleaned_phone = clean_phone_number(customer.phone)
            if cleaned_phone:
                qb_data['PrimaryPhone'] = {
                    'FreeFormNumber': cleaned_phone
                }
        
        # Email (Note: Customer model doesn't have email field, 
        # but we keep the structure for future use)
        # This would need to be added to Customer model if needed
        
        # Address
        address = map_address_to_qb(
            street=customer.street,
            city=customer.city,
            country=customer.country,
            postal_code=customer.postal_code
        )
        if address:
            qb_data['BillAddr'] = address
        
        return qb_data
    
    def _validate_record(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Validate customer data before sending to QuickBooks.
        
        Args:
            data: Mapped customer data
            
        Returns:
            Error message if validation fails, None if valid
        """
        # Customer name is required for QuickBooks
        return validate_required_fields(data, ['DisplayName'])
    
    def _push_to_qb(self, qb_client, data: Dict[str, Any]) -> str:
        """
        Push customer data to QuickBooks.
        
        Args:
            qb_client: QuickBooks API client
            data: Mapped customer data
            
        Returns:
            str: The QuickBooks Customer ID
        """
        try:
            # Import here to handle missing quickbooks module gracefully
            from quickbooks.objects.customer import Customer
            
            display_name = data['DisplayName']
            
            # Check if customer already exists by display name
            existing_customers = Customer.where(
                f"DisplayName = '{display_name}'", 
                qb=qb_client
            )
            
            if existing_customers:
                # Update existing customer
                customer = existing_customers[0]
                
                # Update fields
                if 'PrimaryPhone' in data:
                    customer.PrimaryPhone = data['PrimaryPhone']
                if 'BillAddr' in data:
                    customer.BillAddr = data['BillAddr']
                if 'Notes' in data:
                    customer.Notes = data['Notes']
                
                customer.save(qb=qb_client)
                logger.info(f"Updated existing QuickBooks customer: {customer.Id}")
                return str(customer.Id)
            else:
                # Create new customer
                customer = Customer()
                customer.DisplayName = data['DisplayName']
                
                if 'PrimaryPhone' in data:
                    customer.PrimaryPhone = data['PrimaryPhone']
                if 'BillAddr' in data:
                    customer.BillAddr = data['BillAddr']
                if 'Notes' in data:
                    customer.Notes = data['Notes']
                
                customer.save(qb=qb_client)
                logger.info(f"Created new QuickBooks customer: {customer.Id}")
                return str(customer.Id)
                
        except ImportError as e:
            logger.error(f"QuickBooks module not available: {str(e)}")
            raise QBClientError(f"QuickBooks module not available: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to push customer to QuickBooks: {str(e)}")
            raise QBClientError(f"QuickBooks API error: {str(e)}")
