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
            logger.warning(
                "PostHog is not configured. Analytics events will not be sent."
            )

    def capture(
        self, distinct_id: str, event: str, properties: Optional[Dict[str, Any]] = None
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
        model: Optional[str] = None,
        latency: Optional[float] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        input_messages: Optional[list] = None,
        output_choices: Optional[list] = None,
        thought: Optional[str] = None,
        extra_properties: Optional[Dict[str, Any]] = None,
    ):
        """
        Captures LLM query metadata.
        Uses PostHog's $ai_generation schema for enhanced observability.
        """
        properties = {
            "query": query,
            "SUCCESS": success,
            "attempts": attempts,
            "error_type": error_type,
            "tool_called": tool_called,
            "model": model,
            "$ai_model": model,
            "$ai_latency": latency,
            "$ai_input_tokens": input_tokens,
            "$ai_output_tokens": output_tokens,
            "$ai_input": input_messages,
            "$ai_output_choices": output_choices,
            "$ai_thought": thought,
        }
        if extra_properties:
            properties.update(extra_properties)
        # Capture standard event for backward compatibility and filtering
        self.capture(user_id, "llm_query_processed", properties)

        # Capture $ai_generation for PostHog's specialized AI dashboard
        self.capture(user_id, "$ai_generation", properties)


# Singleton instance
analytics = PostHogClient()
