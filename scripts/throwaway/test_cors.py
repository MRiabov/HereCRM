import os
import asyncio
from fastapi.testclient import TestClient
from src.main import app
from src.config import settings

def test_cors_default():
    # By default, allowed_origins is ["*"]
    client = TestClient(app)
    response = client.options(
        "/api/v1/pwa/dashboard/stats",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        }
    )
    print(f"Default CORS (*): {response.headers.get('access-control-allow-origin')}")
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173" or response.headers.get("access-control-allow-origin") == "*"

def test_cors_restricted():
    # Mock settings to restrict origins
    original_origins = settings.allowed_origins
    settings.allowed_origins = ["https://app.herecrm.com"]
    
    # We need to recreate the middleware or at least the app instance for settings to take effect if they are cached
    # In our case, app.add_middleware is called at module level in src.main.
    # CORSMiddleware reads allow_origins during __init__.
    # So we might need to patch it or reload the module.
    
    # For a quick check, let's just see if we can manually trigger the middleware logic or reload
    import importlib
    import src.main
    importlib.reload(src.main)
    
    client = TestClient(src.main.app)
    
    # Valid origin
    response = client.options(
        "/api/v1/pwa/dashboard/stats",
        headers={
            "Origin": "https://app.herecrm.com",
            "Access-Control-Request-Method": "GET",
        }
    )
    print(f"Restricted CORS (Allowed): {response.headers.get('access-control-allow-origin')}")
    assert response.headers.get("access-control-allow-origin") == "https://app.herecrm.com"

    # Invalid origin
    response = client.options(
        "/api/v1/pwa/dashboard/stats",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "GET",
        }
    )
    print(f"Restricted CORS (Disallowed): {response.headers.get('access-control-allow-origin')}")
    assert response.headers.get("access-control-allow-origin") is None

    # Reset
    settings.allowed_origins = original_origins

if __name__ == "__main__":
    test_cors_default()
    test_cors_restricted()
    print("Verification successful!")
