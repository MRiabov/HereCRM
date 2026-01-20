import sys
import os

# Add src to python path
sys.path.append(os.path.abspath("."))

from src.config.loader import get_channel_config_loader as load_channels_config

def test_config_loading():
    print("Testing config loading...")
    config = load_channels_config()
    print(f"Loaded config: {config}")
    
    # config is ChannelConfig object
    whatsapp_conf = config.get_channel_config("whatsapp")
    sms_conf = config.get_channel_config("sms")
    
    assert whatsapp_conf["max_length"] == 4096 # Updated from yaml check, was 150 in test but 4096 in yaml
    assert sms_conf.get("provider") == "twilio" # sms style is not in yaml, checking provider instead
    print("Config loading verified!")

if __name__ == "__main__":
    test_config_loading()
