from fastapi import APIRouter, Request, Response
import httpx
from src.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_posthog(request: Request, path: str):
    """
    Proxies requests to PostHog to bypass ad-blockers and avoid console errors.
    """
    target_url = f"{settings.posthog_host}/{path}"
    if request.query_params:
        target_url += f"?{request.query_params}"

    # We want to forward the body exactly as is
    body = await request.body()
    
    # Forward headers, but filter out host and potentially other sensitive ones
    # We should keep content-type and others that PostHog needs
    headers = {
        key: value for key, value in request.headers.items() 
        if key.lower() not in ["host", "connection", "accept-encoding"]
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                timeout=10.0
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
            logger.error(f"PostHog proxy error: {e}")
            # Silently fail to avoid console noise if the backend can't reach PostHog
            return Response(status_code=204)
