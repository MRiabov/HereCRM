import secrets
import hashlib
from typing import Tuple, List, Optional
from src.models import IntegrationConfig, IntegrationType
from src.repositories import IntegrationRepository


class IntegrationService:
    def __init__(self, repository: IntegrationRepository):
        self.repository = repository

    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure random string for use as an API key."""
        # Using sk_live_ prefix for professional feel
        return f"sk_live_{secrets.token_urlsafe(32)}"

    @staticmethod
    def hash_key(key: str) -> str:
        """SHA-256 hash the key for secure storage and lookup."""
        return hashlib.sha256(key.encode()).hexdigest()

    async def create_inbound_integration(
        self, business_id: int, label: str
    ) -> Tuple[IntegrationConfig, str]:
        """
        Generate a new API key, hash it, and store the config.
        Returns the config object and the RAW key (which must be shown to the user ONCE).
        """
        raw_key = self.generate_api_key()
        key_hash = self.hash_key(raw_key)

        config = IntegrationConfig(
            business_id=business_id,
            type=IntegrationType.INBOUND_KEY,
            label=label,
            key_hash=key_hash,
            config_payload={"permissions": ["all"]},
            is_active=True,
        )

        self.repository.add(config)
        return config, raw_key

    async def get_active_configs_by_type(
        self, business_id: int, type: IntegrationType
    ) -> List[IntegrationConfig]:
        """Retrieve all active configurations for a given type and business."""
        return await self.repository.get_active_by_type(business_id, type)

    async def validate_key(self, raw_key: str) -> Optional[IntegrationConfig]:
        """Validate an API key and return the associated config if valid."""
        key_hash = self.hash_key(raw_key)
        return await self.repository.get_by_key_hash(key_hash)
