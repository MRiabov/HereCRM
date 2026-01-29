import asyncio
import logging
from src.services.geocoding import GeocodingService

logging.basicConfig(level=logging.INFO)


async def test_geocoding():
    service = GeocodingService()
    address = "high street 34, Dublin"
    print(f"Testing address: {address}")
    lat, lon, street, city, country, postcode, full_address = await service.geocode(
        address
    )
    print(
        f"Result: lat={lat}, lon={lon}, street={street}, city={city}, country={country}, postcode={postcode}"
    )
    print(f"Full Address: {full_address}")

    # Test with default city/country
    address2 = "high street 34"
    print(f"\nTesting address: {address2} with defaults (Dublin, Ireland)")
    lat, lon, street, city, country, postcode, full_address = await service.geocode(
        address2, default_city="Dublin", default_country="Ireland"
    )
    print(
        f"Result: lat={lat}, lon={lon}, street={street}, city={city}, country={country}, postcode={postcode}"
    )
    print(f"Full Address: {full_address}")


if __name__ == "__main__":
    asyncio.run(test_geocoding())
