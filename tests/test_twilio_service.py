"""
Tests for Twilio SMS integration (WP02)
"""

import pytest
from unittest.mock import Mock, patch
from src.services.twilio_service import TwilioService


class TestTwilioService:
    """Test suite for TwilioService"""

    @patch("src.services.twilio_service.settings")
    def test_init_with_credentials(self, mock_settings):
        """Test TwilioService initialization with valid credentials"""
        mock_settings.twilio_account_sid = "test_sid"
        mock_settings.twilio_auth_token = "test_token"
        mock_settings.twilio_phone_number = "+1234567890"

        with patch("src.services.twilio_service.Client") as mock_client:
            service = TwilioService()

            assert service.client is not None
            assert service.from_number == "+1234567890"
            mock_client.assert_called_once_with("test_sid", "test_token")

    @patch("src.services.twilio_service.settings")
    def test_init_without_credentials(self, mock_settings):
        """Test TwilioService initialization without credentials"""
        mock_settings.twilio_account_sid = None
        mock_settings.twilio_auth_token = None
        mock_settings.twilio_phone_number = None

        service = TwilioService()

        assert service.client is None
        assert service.from_number is None

    @pytest.mark.asyncio
    @patch("src.services.twilio_service.settings")
    async def test_send_sms_success(self, mock_settings):
        """Test successful SMS sending"""
        mock_settings.twilio_account_sid = "test_sid"
        mock_settings.twilio_auth_token = "test_token"
        mock_settings.twilio_phone_number = "+1234567890"

        with patch("src.services.twilio_service.Client") as mock_client_class:
            # Setup mock
            mock_client = Mock()
            mock_message = Mock()
            mock_message.sid = "SM123"
            mock_message.status = "queued"
            mock_client.messages.create.return_value = mock_message
            mock_client_class.return_value = mock_client

            service = TwilioService()
            result = await service.send_sms("+9876543210", "Test message")

            assert result is True
            mock_client.messages.create.assert_called_once_with(
                body="Test message", from_="+1234567890", to="+9876543210"
            )

    @pytest.mark.asyncio
    @patch("src.services.twilio_service.settings")
    async def test_send_sms_without_config(self, mock_settings):
        """Test SMS sending fails gracefully without configuration"""
        mock_settings.twilio_account_sid = None
        mock_settings.twilio_auth_token = None
        mock_settings.twilio_phone_number = None

        service = TwilioService()
        result = await service.send_sms("+9876543210", "Test message")

        assert result is False

    @pytest.mark.asyncio
    @patch("src.services.twilio_service.settings")
    async def test_send_sms_twilio_error(self, mock_settings):
        """Test SMS sending handles Twilio API errors"""
        from twilio.base.exceptions import TwilioRestException

        mock_settings.twilio_account_sid = "test_sid"
        mock_settings.twilio_auth_token = "test_token"
        mock_settings.twilio_phone_number = "+1234567890"

        with patch("src.services.twilio_service.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = TwilioRestException(
                status=400, uri="/Messages", msg="Invalid phone number", code=21211
            )
            mock_client_class.return_value = mock_client

            service = TwilioService()
            with pytest.raises(ValueError, match="Invalid recipient phone number"):
                await service.send_sms("+invalid", "Test message")

    @pytest.mark.asyncio
    @patch("src.services.twilio_service.settings")
    async def test_send_sms_validation_errors(self, mock_settings):
        """Test SMS sending fails for invalid inputs"""
        mock_settings.twilio_account_sid = "test_sid"
        mock_settings.twilio_auth_token = "test_token"
        mock_settings.twilio_phone_number = "+1234567890"

        with patch("src.services.twilio_service.Client"):
            service = TwilioService()

            # Empty body
            with pytest.raises(ValueError, match="SMS body cannot be empty"):
                await service.send_sms("+1234567890", "")

            # Too long body
            with pytest.raises(ValueError, match="SMS body too long"):
                await service.send_sms("+1234567890", "a" * 1601)
