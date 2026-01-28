from fastapi import APIRouter, Request, Response
import httpx
from src.config import settings
import logging

logger = logging.getLogger(__name__)

# Reuse client for connection pooling
_client = httpx.AsyncClient()

async def close_client():
    await _client.aclose()

router = APIRouter()

async def proxy_posthog(request: Request, path: str = ""):
    """
    Proxies requests to PostHog to bypass ad-blockers and avoid console errors.
    """
    target_url = f"{settings.posthog_host.rstrip('/')}/{path.lstrip('/')}"
    
    # We want to forward the body exactly as is
    body = await request.body()
    
    # Forward headers, but filter out host and potentially other sensitive ones
    # PostHog needs content-type and user-agent
    headers = {
        key: value for key, value in request.headers.items() 
        if key.lower() not in ["host", "connection", "accept-encoding", "content-length"]
    }

    try:
        resp = await _client.request(
            method=request.method,
            url=target_url,
            content=body,
            params=dict(request.query_params),
            headers=headers,
            timeout=15.0
        )
        
        # Filter response headers to avoid double-compression or length mismatches
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        resp_headers = {
            key: value for key, value in resp.headers.items()
            if key.lower() not in excluded_headers
        }
        
        # Return PostHog response
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=resp_headers
        )
    except Exception as e:
        logger.error(f"PostHog proxy error: {type(e).__name__}: {str(e)} | path: {path} | target: {target_url}")
        # Silently fail to avoid console noise if the backend can't reach PostHog
        return Response(status_code=204)

# Register routes explicitly to ensure deterministic operationId generation
for method in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
    router.add_api_route("", proxy_posthog, methods=[method], include_in_schema=False)
    router.add_api_route("/", proxy_posthog, methods=[method], include_in_schema=False)
    router.add_api_route("/{path:path}", proxy_posthog, methods=[method])
