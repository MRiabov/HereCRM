
import pytest
from unittest.mock import AsyncMock, patch
from src.services.geocoding import GeocodingService

@pytest.mark.asyncio
async def test_nominatim_parsing_success():
    service = GeocodingService()
    
    mock_response = [
        {
            "lat": "53.344",
            "lon": "-6.267",
            "address": {
                "house_number": "34",
                "road": "High Street",
                "suburb": "The Liberties",
                "city": "Dublin",
                "country": "Ireland",
                "postcode": "D08"
            }
        }
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        lat, lon, street, city, country, postcode, full_address = await service.geocode("34 High St", default_city="London")
        
        assert lat == 53.344
        assert lon == -6.267
        assert street == "34 High Street"
        assert city == "Dublin" # Overrides default
        assert country == "Ireland"
        assert postcode == "D08"
        assert "34 High Street, Dublin, Ireland, D08" in full_address

@pytest.mark.asyncio
async def test_nominatim_parsing_fallback():
    service = GeocodingService()
    
    # Simulate missing details but successful lat/lon
    mock_response = [
        {
            "lat": "53.344",
            "lon": "-6.267",
            # No address key
        }
    ]
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        lat, lon, street, city, country, postcode, full_address = await service.geocode("High Street", default_city="Dublin", default_country="Ireland")
        
        assert lat == 53.344
        assert lon == -6.267
        assert street is None
        assert city == "Dublin"
        assert country == "Ireland"
        assert postcode is None
        assert "Dublin, Ireland" in full_address
