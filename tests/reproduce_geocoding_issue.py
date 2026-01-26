
import asyncio
import logging
from src.services.geocoding import GeocodingService

async def test_geocoding():
    service = GeocodingService()
    
    # Test 1: Ambiguous address without country hint
    print("Test 1: Ambiguous address '3 John's Ln W' without country hint")
    lat, lon, street, city, country, postcode, full_address = await service.geocode("3 John's Ln W")
    print(f"Result: {full_address} (Country: {country})")
    
    # Test 2: Ambiguous address with 'Ireland' hint
    print("\nTest 2: Ambiguous address '3 John's Ln W' with 'Ireland' hint")
    lat, lon, street, city, country, postcode, full_address = await service.geocode("3 John's Ln W", default_country="Ireland")
    print(f"Result: {full_address} (Country: {country})")

if __name__ == "__main__":
    asyncio.run(test_geocoding())
