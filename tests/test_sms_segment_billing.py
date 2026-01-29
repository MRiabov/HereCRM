import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.channels.sms_utils import get_sms_segment_count
from src.services.billing_service import BillingService
from src.services.messaging_service import MessagingService


class TestSMSSegmentBilling:
    def test_segment_count_gsm7_short(self):
        # 160 chars or less = 1 segment
        text = "Hello, this is a short test message."
        assert get_sms_segment_count(text) == 1

    def test_segment_count_gsm7_long(self):
        # More than 160 chars = 2+ segments
        text = "This is a much longer message designed to exceed the single segment limit of one hundred and sixty characters in the GSM-7 encoding scheme. We need to keep typing until we are sure it is long enough for this test to pass correctly."
        assert len(text) > 160
        assert get_sms_segment_count(text) >= 2

    def test_segment_count_ucs2(self):
        # Non-GSM char (emoji) = 70 chars per segment
        text = "Hello! 🚀 This message has an emoji."  # 35 chars but contains emoji
        assert len(text) < 70
        # Wait, if it has an emoji, it should still be 1 segment if < 70
        assert get_sms_segment_count(text) == 1

        long_text_with_emoji = "Hello! 🚀 " + "a" * 70
        assert get_sms_segment_count(long_text_with_emoji) >= 2

    @pytest.mark.asyncio
    async def test_messaging_service_calls_billing_with_segments(self):
        # Mock BillingService and Database
        # Since these are locally imported within functions, we patch the source modules.

        with (
            patch(
                "src.services.messaging_service.AsyncSessionLocal"
            ) as mock_db_session_cls,
            patch("src.services.sms_factory.get_sms_service") as mock_get_sms,
            patch(
                "src.services.billing_service.BillingService"
            ) as mock_billing_service_cls,
        ):
            mock_db = AsyncMock()
            mock_db_session_cls.return_value.__aenter__.return_value = mock_db

            mock_sms_service = mock_get_sms.return_value
            mock_sms_service.send_sms = AsyncMock(return_value=True)

            mock_billing_service = mock_billing_service_cls.return_value
            mock_billing_service.track_message_sent = AsyncMock()

            # We need a real-ish MessageLog or at least something that select() accepts.
            # But let's just mock the execute results.
            from src.models import MessageLog

            mock_log = MessageLog(id=1, business_id=123, content="test")

            mock_result = MagicMock()
            mock_result.scalar_one.return_value = mock_log
            mock_db.execute.return_value = mock_result

            service = MessagingService()

            # 1. Test short SMS (1 segment)
            content_short = "Short SMS"
            await service.send_message(
                "+123456789", content_short, channel="SMS", business_id=123
            )

            mock_billing_service.track_message_sent.assert_called_with(123, quantity=1)

            # 2. Test long SMS (2 segments)
            content_long = "A" * 161
            await service.send_message(
                "+123456789", content_long, channel="SMS", business_id=123
            )

            mock_billing_service.track_message_sent.assert_called_with(123, quantity=2)

            # 3. Test emoji message (should be normalized and billed as 1 segment)
            # Re-mock execute to return a new log if needed, but let's just check the last call
            content_emoji = "Hello 🚀"
            await service.send_message(
                "+123456789", content_emoji, channel="SMS", business_id=123
            )

            # Check that it was billed as 1 segment (after normalization "Hello ?" is 7 chars)
            mock_billing_service.track_message_sent.assert_called_with(123, quantity=1)

    @pytest.mark.asyncio
    async def test_billing_service_increments_correctly(self):
        mock_session = AsyncMock()
        with patch(
            "src.services.billing_service.BusinessRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id_global = AsyncMock()

            mock_business = MagicMock()
            mock_business.message_count_current_period = 10
            mock_business.message_credits = 1000
            mock_business.stripe_subscription_id = (
                None  # Skip Stripe report for simple unit test
            )
            mock_repo.get_by_id_global.return_value = mock_business

            service = BillingService(mock_session)
            service.config = {"products": {"messaging": {"price_id": "p1"}}}

            await service.track_message_sent(123, quantity=5)

            assert mock_business.message_count_current_period == 15
            mock_session.commit.assert_called()
