import pytest
import asyncio
from unittest.mock import patch, AsyncMock
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
    # Mock get_coordinates to avoid real API calls during tests
    with patch.object(
        GeocodingService, "get_coordinates", new_callable=AsyncMock
    ) as mock_coords:
        # Mock Big Ben in London
        # Mock Dublin coordinates for reference
        async def side_effect(text):
            if "Big Ben" in text:
                return 51.5007, -0.1246, {"formatted": "Big Ben, London"}
            if "Dublin" in text:
                return 53.3498, -6.2603, {"formatted": "Dublin, Ireland"}
            return None, None, None

        mock_coords.side_effect = side_effect

        (
            lat,
            lon,
            street,
            city,
            country,
            postal_code,
            full_address,
        ) = await service.geocode(
            "Big Ben",
            default_city="Dublin",
            default_country="Ireland",
            safeguard_enabled=True,
            max_distance_km=100.0,
        )

        assert lat is None
        assert lon is None


@pytest.mark.asyncio
async def test_geocoding_safeguard_allowing():
    service = GeocodingService()
    with patch.object(
        GeocodingService, "get_coordinates", new_callable=AsyncMock
    ) as mock_coords:

        async def side_effect(text):
            if "O'Connell Street" in text:
                return (
                    53.3498,
                    -6.2603,
                    {"formatted": "O'Connell Street, Dublin", "city": "Dublin"},
                )
            if "Dublin" in text:
                return 53.3498, -6.2603, {"formatted": "Dublin, Ireland"}
            return None, None, None

        mock_coords.side_effect = side_effect

        (
            lat,
            lon,
            street,
            city,
            country,
            postal_code,
            full_address,
        ) = await service.geocode(
            "O'Connell Street",
            default_city="Dublin",
            default_country="Ireland",
            safeguard_enabled=True,
            max_distance_km=100.0,
        )

        assert lat is not None
        assert lon is not None
        assert "Dublin" in (city or "") or "Dublin" in (full_address or "")


if __name__ == "__main__":
    asyncio.run(test_haversine_distance())
    asyncio.run(test_geocoding_safeguard_blocking())
    asyncio.run(test_geocoding_safeguard_allowing())
    print("All safeguard tests passed!")
