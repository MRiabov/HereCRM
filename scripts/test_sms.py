import asyncio
import logging
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.sms_factory import get_sms_service
from src.config import settings, channels_config


async def test_sms():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 1. Check current config
    sms_config = channels_config.channels.get("sms")
    provider = sms_config.provider if sms_config else "textgrid"
    logger.info(f"Current SMS Provider: {provider}")

    # 2. Get service
    service = get_sms_service()
    logger.info(f"Using service implementation: {service.__class__.__name__}")

    # 3. Test sending (using a dummy number if not configured in env)
    test_number = (
        settings.twilio_phone_number or "+15005550006"
    )  # Standard Twilio test number
    test_body = f"Test message from {provider} via HereCRM factory"

    logger.info(f"Attempting to send test SMS to {test_number}...")

    # Note: This will actually attempt to call the provider if keys are set.
    # For safety in tests, we might want to mock the HTTP call, but for manual verification
    # we expect the agent to check logs.

    success = await service.send_sms(test_number, test_body)

    if success:
        logger.info(
            "✅ SMS Send Command executed successfully (check provider dashboard for delivery)."
        )
    else:
        logger.error("❌ SMS Send Command failed.")


if __name__ == "__main__":
    asyncio.run(test_sms())
