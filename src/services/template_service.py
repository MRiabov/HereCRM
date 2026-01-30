import os
import yaml
import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TemplateService:
    def __init__(self, yaml_path: Optional[str] = None):
        if yaml_path is None:
            # Default path relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            yaml_path = os.path.join(base_dir, "assets", "messages.yaml")

        self.yaml_path = yaml_path
        self.templates = {}
        self.load_templates()

    def load_templates(self):
        if not os.path.exists(self.yaml_path):
            # Fallback to empty if file missing (should not happen in prod)
            self.templates = {}
            return

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            self.templates = yaml.safe_load(f) or {}

    def render(self, template_key: str, **kwargs: Any) -> str:
        template = self.templates.get(template_key)
        if template is None:
            return f"[{template_key}]"  # Return key as fallback

        return self.render_string(template, **kwargs)

    def render_string(self, text: str, **kwargs: Any) -> str:
        """
        Renders a string template by replacing {{var}} or {var} with kwargs.
        Supports dot notation for object attributes.
        """
        if not text:
            return ""

        # Use a more robust way to substitute variables including dot notation
        # We'll normalize {{var}} to {var} and then use format.
        # To avoid issues with literal braces, we'll be careful.
        
        # 1. Normalize {{var.field}} to {var.field}
        # We use a pattern that matches the standard allowed variables
        pattern = r"\{\{([a-zA-Z0-9._-]+)\}\}"
        normalized = re.sub(pattern, r"{\1}", text)

        try:
            # 2. Use string.format() which natively supports dot notation for objects
            return normalized.format(**kwargs)
        except (KeyError, AttributeError, ValueError) as e:
            logger.warning(f"Template rendering issue: {e} in string '{text}'")
            # If format fails, return the normalized version so user sees {missing_var}
            return normalized
        except Exception as e:
            logger.error(f"Unexpected error rendering template string: {e}")
            return text
