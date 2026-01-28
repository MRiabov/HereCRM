from src.main import app
from fastapi.routing import APIRoute

for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"{route.methods} {route.path}")
    else:
        # For mount points or other types of routes
        print(f"OTHER {route.path}")
