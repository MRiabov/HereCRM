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

        # Normalize {{var.field}} to {var.field} for .format()
        # Using a more specific regex to avoid breaking legitimate double braces if any
        normalized = re.sub(r"\{\{([a-zA-Z0-9._-]+)\}\}", r"{\1}", text)

        try:
            return normalized.format(**kwargs)
        except KeyError as e:
            # Missing variable: keep the placeholder
            missing_var = str(e).strip("'")
            logger.warning(f"Missing template variable: {missing_var}")
            # Recursively handle or just return as is. 
            # Simple approach: leave the {var} in place
            return normalized
        except Exception as e:
            logger.error(f"Error rendering template string: {e}")
            return text
