from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import CustomerAvailability
from src.repositories import CustomerAvailabilityRepository


class AvailabilityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.availability_repo = CustomerAvailabilityRepository(session)

    async def add_availability(
        self, customer_id: int, start_time: datetime, end_time: datetime, is_available: bool = True
    ) -> CustomerAvailability:
        if start_time >= end_time:
            raise ValueError("Start time must be before end time")

        availability = CustomerAvailability(
            customer_id=customer_id,
            start_time=start_time,
            end_time=end_time,
            is_available=is_available,
        )
        self.availability_repo.add(availability)
        await self.session.flush()
        return availability

    async def get_availability(
        self, customer_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[CustomerAvailability]:
        return await self.availability_repo.get_for_customer(customer_id, start_date, end_date)

    async def is_customer_available(self, customer_id: int, start_time: datetime, end_time: datetime) -> bool:
        """
        Check if a customer is available during a specific time slot.
        A customer is available if there is at least one availability window that FULLY covers the slot,
        and NO 'unavailable' window overlaps with it.
        (Simple version: just check if it's within ANY 'available' window and NONE of 'unavailable').
        Actually, the requirement is "checking overlap". 
        Typical logic:
        1. Find all intervals for the range.
        2. Customer is available if (Available == True) windows cover the slot AND (Available == False) do not.
        """
        windows = await self.get_availability(customer_id, start_time, end_time)
        
        # Check for any 'unavailable' overlaps first
        for w in windows:
            if not w.is_available:
                # Overlap check
                if w.start_time < end_time and w.end_time > start_time:
                    return False
        
        # Check if it's covered by an 'available' window
        # For simplicity, we assume if is_available=True window covers it
        for w in windows:
            if w.is_available:
                if w.start_time <= start_time and w.end_time >= end_time:
                    return True
        
        return False
