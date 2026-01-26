import pytest
import asyncio
from src.services.geocoding import GeocodingService, calculate_haversine_distance

@pytest.mark.asyncio
async def test_haversine_distance():
    # Dublin to London is ~460km
    dublin = (53.3498, -6.2603)
    london = (51.5074, -0.1278)
    dist = calculate_haversine_distance(dublin[0], dublin[1], london[0], london[1])
    assert 450 < dist < 470

@pytest.mark.asyncio
async def test_geocoding_safeguard_blocking():
    service = GeocodingService()
    try:
        # Dublin as default city
        # Try to geocode something in London (should be blocked)
        lat, lon, street, city, country, postal_code, full_address = await service.geocode(
            "Big Ben",
            default_city="Dublin",
            default_country="Ireland",
            safeguard_enabled=True,
            max_distance_km=100.0
        )
        
        assert lat is None
        assert lon is None
    finally:
        await GeocodingService.close_client()

@pytest.mark.asyncio
async def test_geocoding_safeguard_allowing():
    service = GeocodingService()
    try:
        # Dublin as default city
        # Try to geocode something in Dublin (should be allowed)
        lat, lon, street, city, country, postal_code, full_address = await service.geocode(
            "O'Connell Street",
            default_city="Dublin",
            default_country="Ireland",
            safeguard_enabled=True,
            max_distance_km=100.0
        )
        
        assert lat is not None
        assert lon is not None
        assert "Dublin" in city or "Dublin" in full_address
    finally:
        await GeocodingService.close_client()

if __name__ == "__main__":
    asyncio.run(test_haversine_distance())
    asyncio.run(test_geocoding_safeguard_blocking())
    asyncio.run(test_geocoding_safeguard_allowing())
    print("All safeguard tests passed!")
