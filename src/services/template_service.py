import os
import yaml
import re
import jinja2
from typing import Any, Optional, Dict


class TemplateService:
    def __init__(self, yaml_path: Optional[str] = None):
        # yaml_path argument is kept for backward compatibility in signature.

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if yaml_path is None:
            # Default path: try messages.jinja first, then messages.yaml
            assets_dir = os.path.join(base_dir, "assets")
            if os.path.exists(os.path.join(assets_dir, "messages.jinja")):
                self.template_name = "messages.jinja"
                full_path = os.path.join(assets_dir, "messages.jinja")
            else:
                self.template_name = "messages.yaml"
                full_path = os.path.join(assets_dir, "messages.yaml")
        else:
            full_path = os.path.abspath(yaml_path)
            assets_dir = os.path.dirname(full_path)
            self.template_name = os.path.basename(full_path)

            # Migration logic: if requesting messages.yaml but messages.jinja exists, use jinja
            if self.template_name == "messages.yaml":
                jinja_candidate = os.path.join(assets_dir, "messages.jinja")
                if os.path.exists(jinja_candidate):
                    self.template_name = "messages.jinja"
                    full_path = jinja_candidate

        self.mode = "jinja" if self.template_name.endswith(".jinja") else "yaml"
        self.templates: Dict[str, Any] = {}

        if self.mode == "yaml":
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    self.templates = yaml.safe_load(f) or {}
            else:
                self.templates = {}
        else:
            self.env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(assets_dir),
                autoescape=False,
                undefined=jinja2.Undefined
            )

    def render(self, template_key: str, **kwargs: Any) -> str:
        if self.mode == "yaml":
            template = self.templates.get(template_key)
            if template is None:
                return f"[{template_key}]"

            if not isinstance(template, str):
                return str(template)

            # Normalize {{var}} to {var} for .format()
            normalized_template = re.sub(r"\{\{(.*?)\}\}", r"{\1}", template)

            try:
                return normalized_template.format(**kwargs)
            except Exception:
                return normalized_template
        else:
            # Jinja mode
            try:
                template = self.env.get_template(self.template_name)
                module = template.make_module()

                macro = getattr(module, template_key, None)

                if macro and callable(macro):
                    # Filter kwargs to match macro signature to prevent TypeErrors
                    # Macros have 'arguments' tuple and 'catch_kwargs' boolean
                    if not getattr(macro, 'catch_kwargs', False):
                        valid_keys = set(macro.arguments)
                        filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}
                        return str(macro(**filtered_kwargs))
                    else:
                        return str(macro(**kwargs))
                else:
                    return f"[{template_key}]"
            except Exception as e:
                print(f"Error rendering template '{template_key}': {e}")
                return f"[{template_key}]"
