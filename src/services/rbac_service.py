import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from src.models import UserRole

class RBACService:
    _config: Optional[Dict[str, Any]] = None

    def __init__(self):
        self._load_config()

    def _load_config(self):
        if RBACService._config is None:
            # Determine path to rbac_tools.yaml
            # Assuming structure: src/services/rbac_service.py -> src/assets/rbac_tools.yaml
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / "assets" / "rbac_tools.yaml"
            
            if not config_path.exists():
                # Fallback for different CWD scenarios (e.g. running from root)
                config_path = Path("src/assets/rbac_tools.yaml").resolve()
            
            if not config_path.exists():
                raise FileNotFoundError(f"RBAC configuration not found at {config_path}")

            with open(config_path, "r") as f:
                RBACService._config = yaml.safe_load(f)

    def check_permission(self, user_role: UserRole, tool_name: str) -> bool:
        """
        Check if the given user role has permission to access the specified tool.
        """
        tool_config = self.get_tool_config(tool_name)
        if not tool_config:
            # If tool is not in RBAC config, deny access by default for strictness
            return False

        required_role_str = tool_config.get("role")
        if not required_role_str:
            return False

        # Role hierarchy values
        role_values = {
            "EMPLOYEE": 1,
            "MANAGER": 2,
            "OWNER": 3
        }

        # Normalize user role string
        user_role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
        
        user_level = role_values.get(user_role_str, 0)
        required_level = role_values.get(required_role_str, 100) # Default to max restriction if unknown role

        return user_level >= required_level

    def get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get the configuration for a specific tool.
        """
        if not RBACService._config:
            return None
            
        tools = RBACService._config.get("tools", {})
        return tools.get(tool_name)
