from src.config.loader import get_channel_config_loader as load_channels_config


def test_config_loading():
    """Verify that channel configurations are correctly loaded from YAML."""
    config = load_channels_config()

    # Verify whatsapp configuration
    whatsapp_conf = config.get_channel_config("WHATSAPP")
    assert whatsapp_conf["max_length"] == 4096

    # Verify sms configuration
    sms_conf = config.get_channel_config("SMS")
    assert sms_conf.get("provider") == "twilio"
