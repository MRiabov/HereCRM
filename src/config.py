from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Load .env file explicitly
load_dotenv()


class Settings(BaseSettings):
    openrouter_api_key: str
    whatsapp_app_secret: str
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"

    # Twilio Settings
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None

    # S3 / Storage Settings
    s3_bucket_name: str = "here-crm-exports"
    s3_endpoint_url: Optional[str] = None
    s3_access_key_id: Optional[str] = None
    s3_secret_access_key: Optional[str] = None
    s3_region_name: str = "us-east-1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
