"""Unit tests for LocationService."""

import pytest
from datetime import datetime
from src.services.location_service import LocationService
from src.models import User, Business
from src.database import AsyncSessionLocal


@pytest.mark.asyncio
class TestLocationService:
    """Test suite for LocationService."""

    async def test_update_location(self):
        """Test updating user location."""
        async with AsyncSessionLocal() as db:
            # Create a test business and user
            business = Business(name="Test Business")
            db.add(business)
            await db.flush()

            user = User(
                name="Test Employee",
                business_id=business.id,
                phone_number="+1234567890",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Update location
            test_lat, test_lng = 37.7749, -122.4194
            await LocationService.update_location(db, user.id, test_lat, test_lng)

            # Verify location was updated
            await db.refresh(user)
            assert user.current_latitude == test_lat
            assert user.current_longitude == test_lng
            assert user.location_updated_at is not None
            assert isinstance(user.location_updated_at, datetime)

            # Cleanup
            await db.delete(user)
            await db.delete(business)
            await db.commit()

    async def test_get_employee_location(self):
        """Test retrieving employee location."""
        async with AsyncSessionLocal() as db:
            # Create a test business and user
            business = Business(name="Test Business")
            db.add(business)
            await db.flush()

            user = User(
                name="Test Employee",
                business_id=business.id,
                phone_number="+1234567891",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            # Initially, location should be None
            lat, lng, updated_at = await LocationService.get_employee_location(
                db, user.id
            )
            assert lat is None
            assert lng is None
            assert updated_at is None

            # Update location
            test_lat, test_lng = 40.7128, -74.0060
            await LocationService.update_location(db, user.id, test_lat, test_lng)

            # Retrieve location
            lat, lng, updated_at = await LocationService.get_employee_location(
                db, user.id
            )
            assert lat == test_lat
            assert lng == test_lng
            assert updated_at is not None

            # Cleanup
            await db.delete(user)
            await db.delete(business)
            await db.commit()

    async def test_get_employee_location_nonexistent_user(self):
        """Test retrieving location for non-existent user."""
        async with AsyncSessionLocal() as db:
            lat, lng, updated_at = await LocationService.get_employee_location(
                db, 99999
            )
            assert lat is None
            assert lng is None
            assert updated_at is None


class TestParseLocationFromText:
    """Test suite for parse_location_from_text method."""

    def test_google_maps_at_format(self):
        """Test parsing Google Maps @ format."""
        # Desktop share link
        text = "Check this out: https://www.google.com/maps/@37.7749,-122.4194,15z"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == 37.7749
        assert result[1] == -122.4194

        # Mobile share link
        text2 = "https://maps.google.com/@40.7128,-74.0060,12z"
        result2 = LocationService.parse_location_from_text(text2)
        assert result2 is not None
        assert result2[0] == 40.7128
        assert result2[1] == -74.0060

    def test_google_maps_q_parameter(self):
        """Test parsing Google Maps ?q= parameter."""
        text = "https://maps.google.com/?q=51.5074,-0.1278"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == 51.5074
        assert result[1] == -0.1278

        # With additional parameters
        text2 = "https://maps.google.com/?q=48.8566,2.3522&z=12"
        result2 = LocationService.parse_location_from_text(text2)
        assert result2 is not None
        assert result2[0] == 48.8566
        assert result2[1] == 2.3522

    def test_google_maps_place_format(self):
        """Test parsing Google Maps /place/ format."""
        text = "https://www.google.com/maps/place/35.6762,139.6503"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == 35.6762
        assert result[1] == 139.6503

    def test_apple_maps_ll_parameter(self):
        """Test parsing Apple Maps ll= parameter."""
        text = "https://maps.apple.com/?ll=34.0522,-118.2437"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == 34.0522
        assert result[1] == -118.2437

        # With additional parameters
        text2 = "https://maps.apple.com/?ll=41.8781,-87.6298&q=Chicago"
        result2 = LocationService.parse_location_from_text(text2)
        assert result2 is not None
        assert result2[0] == 41.8781
        assert result2[1] == -87.6298

    def test_generic_coordinates(self):
        """Test parsing plain coordinates."""
        text = "My location: 37.7749,-122.4194"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == 37.7749
        assert result[1] == -122.4194

        # With spaces
        text2 = "I'm at 40.7128, -74.0060"
        result2 = LocationService.parse_location_from_text(text2)
        assert result2 is not None
        assert result2[0] == 40.7128
        assert result2[1] == -74.0060

    def test_negative_coordinates(self):
        """Test parsing negative coordinates."""
        text = "https://maps.google.com/@-33.8688,151.2093,12z"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == -33.8688
        assert result[1] == 151.2093

    def test_invalid_coordinates(self):
        """Test that invalid coordinates are rejected."""
        # Latitude out of range
        text = "https://maps.google.com/@91.0,0.0,12z"
        result = LocationService.parse_location_from_text(text)
        assert result is None

        # Longitude out of range
        text2 = "https://maps.google.com/@0.0,181.0,12z"
        result2 = LocationService.parse_location_from_text(text2)
        assert result2 is None

    def test_no_coordinates_in_text(self):
        """Test text without any coordinates."""
        text = "This is just some random text without coordinates"
        result = LocationService.parse_location_from_text(text)
        assert result is None

        text2 = "https://www.example.com/some-page"
        result2 = LocationService.parse_location_from_text(text2)
        assert result2 is None

    def test_integer_coordinates(self):
        """Test parsing integer coordinates."""
        text = "https://maps.google.com/@40,-74,12z"
        result = LocationService.parse_location_from_text(text)
        assert result is not None
        assert result[0] == 40.0
        assert result[1] == -74.0
