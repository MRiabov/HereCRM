from src.config import settings
import os

print(f"OPENROUTER_API_KEY set: {bool(settings.openrouter_api_key)}")
print(f"OPENROUTER_MODEL: {settings.openrouter_model}")
print(f"ENV OPENROUTER_API_KEY: {bool(os.getenv('OPENROUTER_API_KEY'))}")
