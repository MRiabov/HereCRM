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

    def render_string(self, template_str: str, **kwargs: Any) -> str:
        """
        Renders a string template by replacing {{var}} or {var} with kwargs.
        Supports dot notation for object attributes.
        Handles literal braces in JSON/YAML content by trying to only format intended variables.
        """
        if not template_str:
            return ""

        # Strategy:
        # 1. Identify all patterns we INTEND to substitute: {{var_name}}
        # 2. Replace them with a safe, unique placeholder regular format doesn't touch.
        # 3. Escape ALL remaining braces (turn { into {{, } into }})
        # 4. Restore placeholders to {var_name} so format() hits them.

        # Matches {{variable}} or {variable}
        pattern = r"\{{1,2}([a-zA-Z0-9._-]+)\}{1,2}"

        # Map of placeholder -> original key
        placeholders = {}

        def replace_with_placeholder(match):
            key = match.group(1)
            # Create a unique random-ish placeholder
            placeholder = f"__TEMPLATE_VAR_{len(placeholders)}_{key}__"
            placeholders[placeholder] = key
            return placeholder

        # 1. Replace {{var}} with PLACEHOLDER
        safe_str = re.sub(pattern, replace_with_placeholder, template_str)

        # 2. Escape all remaining literal braces for str.format behavior
        # In str.format, "{{" is literal "{", "}}" is literal "}"
        safe_str = safe_str.replace("{", "{{").replace("}", "}}")

        # 3. Restore placeholders to {key} format
        for placeholder, key in placeholders.items():
            safe_str = safe_str.replace(placeholder, f"{{{key}}}")

        try:
            return safe_str.format(**kwargs)
        except (KeyError, AttributeError, ValueError) as e:
            logger.warning(
                f"Template rendering issue: {e} in string '{template_str[:50]}...'"
            )
            # Fallback A: Try simple string replacement for known keys (ignoring others)
            # This is less robust for complex formatting but safer for literal heavy strings
            fallback = template_str
            for k, v in kwargs.items():
                fallback = fallback.replace(f"{{{{{k}}}}}", str(v))
            return fallback
        except Exception as e:
            logger.error(f"Unexpected error rendering template string: {e}")
            return template_str
