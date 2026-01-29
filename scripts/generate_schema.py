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

# Add project root to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also ensure CWD is project_root for relative file saving
os.chdir(project_root)

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

    # Sort methods for each path to ensure deterministic output
    if "paths" in schema:
        for path in schema["paths"]:
            # sort keys (http methods)
            schema["paths"][path] = dict(sorted(schema["paths"][path].items()))

    # Paths to save
    files_to_save = {
        "herecrm-pwa-openapi.json": lambda f: json.dump(schema, f, indent=2),
        "herecrm-pwa-openapi.yaml": lambda f: yaml.dump(schema, f, sort_keys=False),
    }

    # Determine potential target directories
    # 1. Current directory (Backend root)
    # 2. Sibling PWA directory (if exists)
    target_dirs = ["."]

    # Check for PWA sibling directory
    pwa_sibling = os.path.abspath(os.path.join(os.getcwd(), "..", "HereCRM-PWA"))
    if os.path.isdir(pwa_sibling):
        target_dirs.append(pwa_sibling)
        print(f"Detected PWA sibling at {pwa_sibling}")

    for target_dir in target_dirs:
        for filename, save_fn in files_to_save.items():
            path = os.path.join(target_dir, filename)
            with open(path, "w") as f:
                save_fn(f)
            print(f"Saved {filename} to {target_dir}")


if __name__ == "__main__":
    generate_schema()
