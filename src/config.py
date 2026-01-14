from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file explicitly
load_dotenv()


class Settings(BaseSettings):
    openrouter_api_key: str
    whatsapp_app_secret: str
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
