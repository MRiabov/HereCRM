import logging
import posthog
from typing import Any, Dict, Optional
from src.config import settings

logger = logging.getLogger(__name__)

class PostHogClient:
    def __init__(self):
        self.api_key = settings.posthog_api_key
        self.host = settings.posthog_host
        self.enabled = bool(self.api_key)
        
        if self.enabled and self.api_key:
            self.client: Optional[posthog.Posthog] = posthog.Posthog(
                self.api_key, host=self.host
            )
        else:
            self.client = None
            logger.warning("PostHog is not configured. Analytics events will not be sent.")

    def capture(
        self, 
        distinct_id: str, 
        event: str, 
        properties: Optional[Dict[str, Any]] = None
    ):
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.capture(distinct_id, event, properties)
        except Exception as e:
            logger.error(f"Failed to capture PostHog event '{event}': {e}")

    def capture_llm_query(
        self, 
        user_id: str, 
        query: str, 
        success: bool, 
        attempts: int,
        error_type: Optional[str] = None,
        tool_called: Optional[str] = None,
        model: Optional[str] = None
    ):
        properties = {
            "query": query,
            "success": success,
            "attempts": attempts,
            "error_type": error_type,
            "tool_called": tool_called,
            "model": model,
        }
        self.capture(user_id, "llm_query_processed", properties)

# Singleton instance
analytics = PostHogClient()
