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
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Resolve an address string to latitude and longitude using OpenStreetMap Nominatim API.
        Returns: (latitude, longitude) or (None, None) if not found or error.
        """
        if not address:
            return None, None

        params = {"q": address, "format": "json", "limit": 1}
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
                    return lat, lon

                logger.info(f"No results found for address: {address}")
                return None, None

        except httpx.HTTPError as e:
            logger.error(f"Geocoding error for address '{address}': {e}")
            return None, None
        except (ValueError, KeyError) as e:
            logger.error(f"Error parsing geocoding response: {e}")
            return None, None

    async def geocode(
        self, address: str
    ) -> Tuple[
        Optional[float], Optional[float], Optional[str], Optional[str], Optional[str]
    ]:
        """
        Geocodes an address and returns (lat, lon, street, city, country).
        """
        lat, lon = await self.get_coordinates(address)
        # For now, we only get lat/lon from the current Nominatim implementation
        return lat, lon, None, None, None
