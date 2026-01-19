import sys
import os

# Add src to python path
sys.path.append(os.path.abspath("."))

from src.config import load_channels_config

def test_config_loading():
    print("Testing config loading...")
    config = load_channels_config()
    print(f"Loaded config: {config}")
    
    assert config.channels["whatsapp"].max_length == 150
    assert config.channels["sms"].style == "very concise"
    print("Config loading verified!")

if __name__ == "__main__":
    test_config_loading()
