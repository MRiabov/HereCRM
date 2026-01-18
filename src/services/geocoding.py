import httpx
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GeocodingService:
    def __init__(self, user_agent: str = "WhatsAppCRM/1.0"):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.user_agent = user_agent

    async def get_coordinates(
        self, address: str
    ) -> Tuple[Optional[float], Optional[float], Optional[dict]]:
        """
        Resolve an address string using Nominatim API.
        Returns: (latitude, longitude, address_details) or (None, None, None).
        """
        if not address:
            return None, None, None

        params = {"q": address, "format": "json", "limit": 1, "addressdetails": 1}
        headers = {"User-Agent": self.user_agent}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url, params=params, headers=headers, timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if data and isinstance(data, list) and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    details = data[0].get("address", {})
                    return lat, lon, details

                logger.info(f"No results found for address: {address}")
                return None, None, None

        except httpx.HTTPError as e:
            logger.error(f"Geocoding error for address '{address}': {e}")
            return None, None, None
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing geocoding response: {e}")
            return None, None, None

    async def geocode(
        self, 
        address: str,
        default_city: Optional[str] = None,
        default_country: Optional[str] = None
    ) -> Tuple[
        Optional[float], Optional[float], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        """
        Geocodes an address and returns (lat, lon, street, city, country, postal_code).
        """
        query_address = address
        parts = []
        if default_city and default_city.lower() not in address.lower():
             parts.append(default_city)
        if default_country and default_country.lower() not in address.lower():
             parts.append(default_country)
        
        if parts:
            query_address = f"{address}, {', '.join(parts)}"

        lat, lon, details = await self.get_coordinates(query_address)
        
        if not lat and query_address != address:
            # Fallback to original address if enhanced query fails
            lat, lon, details = await self.get_coordinates(address)

        if not details:
            return lat, lon, None, default_city, default_country, None

        # Parse address details
        street_name = details.get("road")
        house_number = details.get("house_number")
        street = f"{house_number} {street_name}" if house_number and street_name else (street_name or house_number)
        
        city = details.get("city") or details.get("town") or details.get("village") or details.get("suburb") or default_city
        country = details.get("country") or default_country
        postcode = details.get("postcode")

        return lat, lon, street, city, country, postcode
