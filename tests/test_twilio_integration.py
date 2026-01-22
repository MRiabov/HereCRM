import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from src.services.whatsapp_service import WhatsappService
from src.services.messaging_service import MessagingService
from src.models import User, ConversationState, ConversationStatus
from src.services.template_service import TemplateService
from src.llm_client import LLMParser
from src.config import settings

@pytest.mark.asyncio
async def test_whatsapp_service_sends_via_twilio():
    """
    Verify that WhatsappService.handle_message uses TwilioService to send SMS
    when channel is 'sms'.
    """
    # Mock settings to ensure TwilioService initializes its client
    with patch('src.services.twilio_service.settings') as mock_settings:
        mock_settings.twilio_account_sid = "AC_TEST"
        mock_settings.twilio_auth_token = "AUTH_TEST"
        mock_settings.twilio_phone_number = "+15005550006"

        # Mock the Twilio Client class
        with patch('src.services.twilio_service.Client') as MockClient:
            mock_twilio_client = MagicMock()
            MockClient.return_value = mock_twilio_client

            mock_message = MagicMock()
            mock_message.sid = "SM_TEST_ID"
            mock_message.status = "queued"
            mock_twilio_client.messages.create.return_value = mock_message

            # Setup WhatsappService dependencies
            session = AsyncMock()
            # Configure session.add to be synchronous
            session.add = MagicMock()

            parser = AsyncMock(spec=LLMParser)
            # Make sure parser returns a string so we don't go into tool execution logic for this simple test
            parser.parse.return_value = "This is a reply"

            template_service = MagicMock(spec=TemplateService)
            # Render returns the template key so we know what was rendered
            template_service.render.side_effect = lambda key, **kwargs: f"TEMPLATE:{key}"

            # Pass mock billing service in constructor
            service = WhatsappService(session, parser, template_service, billing_service=AsyncMock())

            # Mock repos
            service.user_repo = AsyncMock()
            service.state_repo = AsyncMock()
            service.business_repo = AsyncMock()
            # service.billing_service is already mocked via constructor

            # Mock User and State
            user = MagicMock(spec=User)
            user.id = 1
            user.phone_number = "+1234567890"
            user.business_id = 1
            # Return user for both get_by_id and get_by_phone
            service.user_repo.get_by_id.return_value = user
            service.user_repo.get_by_phone.return_value = user

            state_record = MagicMock(spec=ConversationState)
            state_record.state = ConversationStatus.IDLE
            state_record.active_channel = "sms"
            service.state_repo.get_by_user_id.return_value = state_record

            # Mock ServiceRepository which is instantiated inside _handle_idle
            with patch('src.services.whatsapp_service.ServiceRepository') as MockServiceRepo:
                mock_service_repo = AsyncMock()
                MockServiceRepo.return_value = mock_service_repo
                mock_service_repo.get_all_for_business.return_value = []

                # Execute
                # Use non-greeting text to trigger parser
                response = await service.handle_message(
                    message_text="Do something",
                    user_id=1,
                    channel="sms"
                )

            print(f"DEBUG: Response was: '{response}'")

            # Assertions
            assert response == "This is a reply"

            # Verify Twilio Client was called
            mock_twilio_client.messages.create.assert_called_once()
            call_args = mock_twilio_client.messages.create.call_args
            assert call_args.kwargs['to'] == "+1234567890"
            assert call_args.kwargs['body'] == "This is a reply"
            assert call_args.kwargs['from_'] == "+15005550006"


@pytest.mark.asyncio
async def test_messaging_service_sends_via_twilio():
    """
    Verify that MessagingService.send_message uses TwilioService to send SMS
    when channel is 'sms'.
    """
    # Mock settings
    with patch('src.services.twilio_service.settings') as mock_settings:
        mock_settings.twilio_account_sid = "AC_TEST"
        mock_settings.twilio_auth_token = "AUTH_TEST"
        mock_settings.twilio_phone_number = "+15005550006"

        # Mock Twilio Client
        with patch('src.services.twilio_service.Client') as MockClient:
            mock_twilio_client = MagicMock()
            MockClient.return_value = mock_twilio_client

            mock_message = MagicMock()
            mock_message.sid = "SM_TEST_ID"
            mock_message.status = "sent"
            mock_twilio_client.messages.create.return_value = mock_message

            service = MessagingService()

            # We need to mock the database interactions in MessagingService
            with patch('src.services.messaging_service.AsyncSessionLocal') as MockDB:
                mock_db = AsyncMock()
                # Make add synchronous
                mock_db.add = MagicMock()
                MockDB.return_value.__aenter__.return_value = mock_db

                # Mock execute result for reloading message_log
                mock_result = MagicMock()
                mock_msg_log = MagicMock()
                mock_result.scalar_one.return_value = mock_msg_log
                mock_db.execute.return_value = mock_result

                # Execute
                await service.send_message(
                    recipient_phone="+1234567890",
                    content="Job Update",
                    channel="sms",
                    business_id=1
                )

                # Verify Twilio Client was called
                mock_twilio_client.messages.create.assert_called_once()
                call_args = mock_twilio_client.messages.create.call_args
                assert call_args.kwargs['to'] == "+1234567890"
                assert call_args.kwargs['body'] == "Job Update"
                assert call_args.kwargs['from_'] == "+15005550006"

                # Verify status update
                assert mock_msg_log.status == "sent"  # MessageStatus.SENT is 'sent'
