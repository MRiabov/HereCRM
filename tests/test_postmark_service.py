"""
Tests for Postmark Email integration (WP03)
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.services.postmark_service import PostmarkService


class TestPostmarkService:
    """Test suite for PostmarkService"""

    @patch("src.services.postmark_service.settings")
    def test_init_with_credentials(self, mock_settings):
        """Test PostmarkService initialization with valid credentials"""
        mock_settings.postmark_server_token = "test_token"
        mock_settings.from_email_address = "test@example.com"

        service = PostmarkService()

        assert service.server_token == "test_token"
        assert service.from_email == "test@example.com"
        assert service.api_url == "https://api.postmarkapp.com/email"

    @patch("src.services.postmark_service.settings")
    def test_init_without_credentials(self, mock_settings):
        """Test PostmarkService initialization without credentials"""
        mock_settings.postmark_server_token = None
        mock_settings.from_email_address = None

        service = PostmarkService()

        assert service.server_token is None
        assert service.from_email is None

    @pytest.mark.asyncio
    @patch("src.services.postmark_service.settings")
    async def test_send_email_success(self, mock_settings):
        """Test successful email sending"""
        mock_settings.postmark_server_token = "test_token"
        mock_settings.from_email_address = "sender@example.com"

        with patch(
            "src.services.postmark_service.httpx.AsyncClient"
        ) as mock_client_class:
            # Setup mock
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"MessageID": "msg-123"}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            service = PostmarkService()
            result = await service.send_email(
                to_email="recipient@example.com",
                subject="Test Subject",
                body="Test body",
            )

            assert result is True
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://api.postmarkapp.com/email"
            assert call_args[1]["json"]["To"] == "recipient@example.com"
            assert call_args[1]["json"]["Subject"] == "Test Subject"
            assert call_args[1]["json"]["TextBody"] == "Test body"

    @pytest.mark.asyncio
    @patch("src.services.postmark_service.settings")
    async def test_send_email_with_threading(self, mock_settings):
        """Test email sending with threading headers"""
        mock_settings.postmark_server_token = "test_token"
        mock_settings.from_email_address = "sender@example.com"

        with patch(
            "src.services.postmark_service.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"MessageID": "msg-123"}
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            service = PostmarkService()
            result = await service.send_email(
                to_email="recipient@example.com",
                subject="Re: Test",
                body="Reply body",
                in_reply_to="<original-msg-id>",
                references="<ref-1> <ref-2>",
            )

            assert result is True
            call_args = mock_client.post.call_args
            headers = call_args[1]["json"]["Headers"]
            assert len(headers) == 2
            assert {"Name": "In-Reply-To", "Value": "<original-msg-id>"} in headers
            assert {"Name": "References", "Value": "<ref-1> <ref-2>"} in headers

    @pytest.mark.asyncio
    @patch("src.services.postmark_service.settings")
    async def test_send_email_without_config(self, mock_settings):
        """Test email sending fails gracefully without configuration"""
        mock_settings.postmark_server_token = None
        mock_settings.from_email_address = None

        service = PostmarkService()
        result = await service.send_email(
            to_email="recipient@example.com", subject="Test", body="Test body"
        )

        assert result is False

    @pytest.mark.asyncio
    @patch("src.services.postmark_service.settings")
    async def test_send_email_api_error(self, mock_settings):
        """Test email sending handles API errors"""
        mock_settings.postmark_server_token = "test_token"
        mock_settings.from_email_address = "sender@example.com"

        with patch(
            "src.services.postmark_service.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.text = "Invalid email address"
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            service = PostmarkService()
            result = await service.send_email(
                to_email="invalid-email", subject="Test", body="Test body"
            )

            assert result is False

    @pytest.mark.asyncio
    @patch("src.services.postmark_service.settings")
    async def test_send_email_timeout(self, mock_settings):
        """Test email sending handles timeout errors"""
        import httpx

        mock_settings.postmark_server_token = "test_token"
        mock_settings.from_email_address = "sender@example.com"

        with patch(
            "src.services.postmark_service.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            service = PostmarkService()
            result = await service.send_email(
                to_email="recipient@example.com", subject="Test", body="Test body"
            )

            assert result is False
