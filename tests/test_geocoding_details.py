import pytest
from unittest.mock import AsyncMock, patch
from src.services.geocoding import GeocodingService


@pytest.mark.asyncio
async def test_nominatim_parsing_success():
    service = GeocodingService()

    mock_response = {
        "results": [
            {
                "lat": 53.344,
                "lon": -6.267,
                "street": "High Street",
                "housenumber": "34",
                "city": "Dublin",
                "country": "Ireland",
                "postcode": "D08",
                "formatted": "34 High Street, Dublin, Ireland, D08",
            }
        ]
    }

    with patch("src.services.geocoding.GeocodingService.get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = AsyncMock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        lat, lon, street, city, country, postcode, full_address = await service.geocode(
            "34 High St", default_city="London"
        )

        assert lat == 53.344
        assert lon == -6.267
        assert street == "34 High Street"
        assert city == "Dublin"  # Overrides default
        assert country == "Ireland"
        assert postcode == "D08"
        assert "34 High Street, Dublin, Ireland, D08" in full_address


@pytest.mark.asyncio
async def test_nominatim_parsing_fallback():
    service = GeocodingService()

    # Simulate missing details but successful lat/lon
    mock_response = {
        "results": [
            {
                "lat": 53.344,
                "lon": -6.267,
                # No other fields
            }
        ]
    }

    with patch("src.services.geocoding.GeocodingService.get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.get.return_value = AsyncMock(
            status_code=200, json=lambda: mock_response, raise_for_status=lambda: None
        )

        lat, lon, street, city, country, postcode, full_address = await service.geocode(
            "High Street", default_city="Dublin", default_country="Ireland"
        )

        assert lat == 53.344
        assert lon == -6.267
        assert street is None
        assert city == "Dublin"
        assert country == "Ireland"
        assert postcode is None
        assert "Dublin, Ireland" in full_address
