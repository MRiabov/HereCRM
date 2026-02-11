from typing import Optional, Dict
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel
import yaml
import os

# Load .env file explicitly
load_dotenv()


class Settings(BaseSettings):
    openrouter_api_key: str
    whatsapp_app_secret: str
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_verify_token: Optional[str] = "blue_cat_123"  # Default or env
    whatsapp_api_version: str = "v18.0"
    waba_id: Optional[str] = None

    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"

    # Twilio Settings
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

    # TextGrid Settings
    textgrid_account_sid: Optional[str] = None
    textgrid_auth_token: Optional[str] = None
    textgrid_phone_number: Optional[str] = None

    # Postmark Settings
    postmark_server_token: Optional[str] = None
    from_email_address: Optional[str] = None
    postmark_auth_user: Optional[str] = None
    postmark_auth_pass: Optional[str] = None

    # S3 / Storage Settings
    s3_bucket_name: str = "here-crm-exports"
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_region_name: str = "us-east-1"

    # Generic Webhook Settings
    generic_webhook_secret: Optional[str] = None

    # OpenRouteService
    openrouteservice_api_key: Optional[str] = None

    # GeoApify
    geoapify_key: Optional[str] = None

    # Google Calendar Integration
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: Optional[str] = None

    # PostHog Settings
    posthog_api_key: Optional[str] = None
    posthog_host: str = "https://eu.i.posthog.com"

    # Dev Mode
    dev_mode: bool = False
    automigrate: bool = False

    # Security
    secret_key: str = "dev_secret_key_change_me_in_production"
    allowed_origins: list[str] = ["*"]

    # Clerk Settings
    clerk_secret_key: Optional[str] = None
    clerk_publishable_key: Optional[str] = None
    clerk_issuer: Optional[str] = None
    clerk_jwks_url: Optional[str] = None
    clerk_webhook_secret: Optional[str] = None
    clerk_sign_up_url: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ChannelSettings(BaseModel):
    max_length: int
    style: str
    provider: Optional[str] = "textgrid"


class ChannelsConfig(BaseModel):
    channels: Dict[str, ChannelSettings]


def load_channels_config() -> ChannelsConfig:
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "assets", "channels.yaml")

    if not os.path.exists(config_path):
        # Default configuration if file is missing
        return ChannelsConfig(
            channels={
                "WHATSAPP": ChannelSettings(max_length=150, style="concise"),
                "email": ChannelSettings(max_length=1000, style="detailed"),
                "SMS": ChannelSettings(
                    max_length=160, style="direct", provider="textgrid"
                ),
            }
        )

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
        return ChannelsConfig(
            channels={k: ChannelSettings(**v) for k, v in data.items()}
        )


settings = Settings()
channels_config = load_channels_config()
