import os
import yaml
import re
from typing import Any, Optional


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

        # Normalize {{var}} to {var} for .format()
        # This regex finds {{something}} and replaces it with {something}
        normalized_template = re.sub(r"\{\{(.*?)\}\}", r"{\1}", template)

        try:
            return normalized_template.format(**kwargs)
        except KeyError:
            # If a key is missing, return the template as is or with placeholders
            return normalized_template
        except Exception:
            return normalized_template
