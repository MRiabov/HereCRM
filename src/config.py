from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file explicitly
load_dotenv()


class Settings(BaseSettings):
    google_api_key: str
    whatsapp_app_secret: str
    gemini_model: str = "gemini-3-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
