from functools import lru_cache
from src.config import channels_config
from src.services.channels.base import SMSMessagingService
from src.services.channels.textgrid import TextGridService
from src.services.twilio_service import TwilioService


@lru_cache()
def get_sms_service() -> SMSMessagingService:
    """
    Factory function to get the configured SMS messaging service.
    Defaults to TextGridService.
    """
    # Get configuration for the 'SMS' channel
    # Defaulting to 'textgrid' as per requirements
    sms_config = channels_config.channels.get("SMS")
    provider = (
        sms_config.provider.lower()
        if sms_config and sms_config.provider
        else "textgrid"
    )

    if provider == "twilio":
        return TwilioService()
    else:
        # Default to TextGrid
        return TextGridService()
