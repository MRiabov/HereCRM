import os
import json
import yaml
import sys

# Set dummy env vars BEFORE importing anything from src to avoid validation errors
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "dummy")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "dummy")
os.environ.setdefault("WHATSAPP_VERIFY_TOKEN", "dummy")
os.environ.setdefault("WABA_ID", "dummy")
os.environ.setdefault("OPENROUTER_API_KEY", "dummy")
os.environ.setdefault("WHATSAPP_APP_SECRET", "dummy")
os.environ.setdefault("POSTHOG_API_KEY", "dummy")
os.environ.setdefault("POSTHOG_HOST", "http://localhost")
os.environ.setdefault("CLERK_SECRET_KEY", "dummy")
os.environ.setdefault("CLERK_PUBLISHABLE_KEY", "dummy")
os.environ.setdefault("CLERK_ISSUER", "dummy")
os.environ.setdefault("CLERK_JWKS_URL", "https://example.com/.well-known/jwks.json")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "dummy")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "dummy")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "dummy")
os.environ.setdefault("OPENROUTESERVICE_API_KEY", "dummy")
os.environ.setdefault("S3_ACCESS_KEY_ID", "dummy")
os.environ.setdefault("S3_SECRET_ACCESS_KEY", "dummy")
os.environ.setdefault("STRIPE_SECRET_KEY", "dummy")
os.environ.setdefault("SECRET_KEY", "dummy")

# Add src to sys.path if not present
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from fastapi import FastAPI
try:
    from src.api.v1.pwa.router import router as pwa_router
except ImportError as e:
    print(f"Error importing router: {e}")
    sys.exit(1)

def generate_schema():
    print("Generating PWA OpenAPI Schema...")
    # Create a temporary app to generate the schema
    # We use the same title and version as in the existing schema file
    app = FastAPI(title="HereCRM PWA API", version="1.0.0")

    # Mount the PWA router with the correct prefix
    app.include_router(pwa_router, prefix="/api/v1/pwa")

    schema = app.openapi()

    # Save JSON
    json_path = "herecrm-pwa-openapi.json"
    with open(json_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Saved JSON schema to {json_path}")

    # Save YAML
    yaml_path = "herecrm-pwa-openapi.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(schema, f, sort_keys=False)
    print(f"Saved YAML schema to {yaml_path}")

if __name__ == "__main__":
    generate_schema()
