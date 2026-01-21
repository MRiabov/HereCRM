"""Location service for managing employee location data."""

import re
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import User


class LocationService:
    """Service for managing employee location tracking."""
    
    @staticmethod
    async def update_location(
        db: AsyncSession,
        user_id: int,
        lat: float,
        lng: float
    ) -> None:
        """
        Update the location of a user.
        
        Args:
            db: Database session
            user_id: ID of the user to update
            lat: Latitude coordinate
            lng: Longitude coordinate
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            user.current_latitude = lat
            user.current_longitude = lng
            user.location_updated_at = datetime.now(timezone.utc)
            await db.commit()
    
    @staticmethod
    async def get_employee_location(
        db: AsyncSession,
        user_id: int
    ) -> Tuple[Optional[float], Optional[float], Optional[datetime]]:
        """
        Get the current location of an employee.
        
        Args:
            db: Database session
            user_id: ID of the user
            
        Returns:
            Tuple of (latitude, longitude, last_updated_timestamp)
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            return (
                user.current_latitude,
                user.current_longitude,
                user.location_updated_at
            )
        
        return (None, None, None)
    
    @staticmethod
    def parse_location_from_text(text: str) -> Optional[Tuple[float, float]]:
        """
        Extract latitude and longitude coordinates from map URLs in text.
        
        Supports:
        - Google Maps: maps.google.com, goo.gl/maps, maps.app.goo.gl
        - Apple Maps: maps.apple.com
        
        Args:
            text: Text potentially containing a map URL
            
        Returns:
            Tuple of (latitude, longitude) if found, None otherwise
        """
        # Pattern 1: Google Maps with @lat,lng format
        # Example: https://www.google.com/maps/@37.7749,-122.4194,15z
        # Example: https://maps.google.com/@37.7749,-122.4194,15z
        google_at_pattern = r'(?:maps\.google\.com|google\.com/maps)/@(-?\d+\.?\d*),(-?\d+\.?\d*)'
        match = re.search(google_at_pattern, text)
        if match:
            try:
                lat, lng = float(match.group(1)), float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except ValueError:
                pass
        
        # Pattern 2: Google Maps with ?q= or &q= query parameter
        # Example: https://maps.google.com/?q=37.7749,-122.4194
        google_q_pattern = r'(?:maps\.google\.com|google\.com/maps).*[?&]q=(-?\d+\.?\d*),(-?\d+\.?\d*)'
        match = re.search(google_q_pattern, text)
        if match:
            try:
                lat, lng = float(match.group(1)), float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except ValueError:
                pass
        
        # Pattern 3: Google Maps with /place/ or /search/ followed by coordinates
        # Example: https://www.google.com/maps/place/37.7749,-122.4194
        google_place_pattern = r'(?:maps\.google\.com|google\.com/maps)/(?:place|search)/[^/]*?(-?\d+\.?\d*),(-?\d+\.?\d*)'
        match = re.search(google_place_pattern, text)
        if match:
            try:
                lat, lng = float(match.group(1)), float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except ValueError:
                pass
        
        # Pattern 4: Apple Maps with ll= parameter
        # Example: https://maps.apple.com/?ll=37.7749,-122.4194
        apple_ll_pattern = r'maps\.apple\.com.*[?&]ll=(-?\d+\.?\d*),(-?\d+\.?\d*)'
        match = re.search(apple_ll_pattern, text)
        if match:
            try:
                lat, lng = float(match.group(1)), float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except ValueError:
                pass
        
        # Pattern 5: Generic lat,lng pattern (fallback for plain coordinates)
        # Example: "My location: 37.7749,-122.4194"
        generic_pattern = r'(-?\d+\.?\d+)\s*,\s*(-?\d+\.?\d+)'
        match = re.search(generic_pattern, text)
        if match:
            try:
                lat, lng = float(match.group(1)), float(match.group(2))
                # Only accept if values are in valid lat/lng ranges
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return (lat, lng)
            except ValueError:
                pass
        
        return None

