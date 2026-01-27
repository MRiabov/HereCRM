import httpx
import math
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees) in kilometers.
    """
    # Convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles
    return c * r


class GeocodingService:
    _shared_client: Optional[httpx.AsyncClient] = None

    def __init__(self):
        from src.config import settings
        self.base_url = "https://api.geoapify.com/v1/geocode/search"
        self.api_key = settings.geoapify_key

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(timeout=10.0)
        return cls._shared_client

    @classmethod
    async def close_client(cls):
        if cls._shared_client:
            await cls._shared_client.aclose()
            cls._shared_client = None

    async def get_coordinates(
        self, address: str
    ) -> Tuple[Optional[float], Optional[float], Optional[dict]]:
        """
        Resolve an address string using GeoApify API.
        Returns: (latitude, longitude, properties) or (None, None, None).
        """
        if not address or not self.api_key:
            if not self.api_key:
                logger.error("GeoApify API key is missing.")
            return None, None, None

        params = {"text": address, "format": "json", "limit": 1, "apiKey": self.api_key}

        try:
            client = self.get_client()
            response = await client.get(
                self.base_url, params=params
            )
            response.raise_for_status()
            data = response.json()

            if data and "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                # GeoApify returns details in the result object itself
                return lat, lon, result

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
        default_country: Optional[str] = None,
        safeguard_enabled: bool = False,
        max_distance_km: float = 100.0
    ) -> Tuple[
        Optional[float], Optional[float], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]
    ]:
        """
        Geocodes an address and returns (lat, lon, street, city, country, postal_code, full_address).
        If safeguard is enabled and default_city is provided, ensures result is within max_distance_km.
        """
        query_address = address
        parts = []
        if default_city:
            parts.append(default_city)
        if default_country:
            parts.append(default_country)
            
        if parts:
            query_address = f"{address}, {', '.join(parts)}"

        lat, lon, details = await self.get_coordinates(query_address)
        
        if not lat and query_address != address:
            # Fallback to original address if enhanced query fails
            lat, lon, details = await self.get_coordinates(address)

        # Apply Safeguard
        if safeguard_enabled and default_city and lat and lon:
            # Get coordinates for the default city to check distance
            ref_lat, ref_lon, _ = await self.get_coordinates(f"{default_city}, {default_country}" if default_country else default_city)
            if ref_lat and ref_lon:
                distance = calculate_haversine_distance(ref_lat, ref_lon, lat, lon)
                if distance > max_distance_km:
                    logger.warning(f"Geocoding result for '{address}' is {distance:.2f}km away from {default_city}, exceeding safeguard limit of {max_distance_km}km.")
                    return None, None, None, None, None, None, None

        if not details:
            street = None
            city = default_city
            country = default_country
            postcode = None
            
            addr_parts = [p for p in [street, city, country, postcode] if p]
            full_address = ", ".join(addr_parts) if addr_parts else address
            return lat, lon, street, city, country, postcode, full_address

        # Parse GeoApify address details
        street = details.get("street")
        house_number = details.get("housenumber") or details.get("house_number")
        if house_number and street:
            street = f"{house_number} {street}"
        elif house_number:
            street = house_number
        
        city = details.get("city") or details.get("municipality") or default_city
        country = details.get("country") or default_country
        postcode = details.get("postcode")
        full_address = details.get("formatted") or address

        return lat, lon, street, city, country, postcode, full_address
