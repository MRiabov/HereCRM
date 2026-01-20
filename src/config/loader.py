import os
import yaml
from functools import lru_cache
from typing import Dict, Any

class ChannelConfig:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to channels.yaml in the same directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "channels.yaml")
        
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}

    def get_channel_config(self, channel_name: str) -> Dict[str, Any]:
        return self.config.get("channels", {}).get(channel_name, {})

@lru_cache()
def get_channel_config_loader() -> ChannelConfig:
    return ChannelConfig()
