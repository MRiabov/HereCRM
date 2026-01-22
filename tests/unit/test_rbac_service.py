import pytest
from unittest.mock import patch, mock_open
from src.services.rbac_service import RBACService
from src.models import UserRole

MOCK_RBAC_CONFIG = """
tools:
  TestEmployeeTool:
    role: employee
    friendly_name: "employee tool"
  TestManagerTool:
    role: manager
    friendly_name: "manager tool"
  TestOwnerTool:
    role: owner
    friendly_name: "owner tool"
"""

@pytest.fixture
def rbac_service():
    # Reset the singleton config before each test to ensure fresh load
    RBACService._config = None
    with patch("builtins.open", mock_open(read_data=MOCK_RBAC_CONFIG)):
        with patch("src.services.rbac_service.Path.exists", return_value=True):
             service = RBACService()
             return service

def test_load_config(rbac_service):
    assert rbac_service.get_tool_config("TestEmployeeTool") is not None
    assert rbac_service.get_tool_config("TestManagerTool")["role"] == "manager"

def test_employee_access(rbac_service):
    # Employee should access employee tools only
    assert rbac_service.check_permission(UserRole.EMPLOYEE, "TestEmployeeTool") is True
    assert rbac_service.check_permission(UserRole.EMPLOYEE, "TestManagerTool") is False
    assert rbac_service.check_permission(UserRole.EMPLOYEE, "TestOwnerTool") is False

def test_manager_access(rbac_service):
    # Manager access employee and manager tools, not owner
    assert rbac_service.check_permission(UserRole.MANAGER, "TestEmployeeTool") is True
    assert rbac_service.check_permission(UserRole.MANAGER, "TestManagerTool") is True
    assert rbac_service.check_permission(UserRole.MANAGER, "TestOwnerTool") is False

def test_owner_access(rbac_service):
    # Owner access everything
    assert rbac_service.check_permission(UserRole.OWNER, "TestEmployeeTool") is True
    assert rbac_service.check_permission(UserRole.OWNER, "TestManagerTool") is True
    assert rbac_service.check_permission(UserRole.OWNER, "TestOwnerTool") is True

def test_unknown_tool(rbac_service):
    # Default deny
    assert rbac_service.check_permission(UserRole.OWNER, "UnknownTool") is False

def test_get_tool_config(rbac_service):
    config = rbac_service.get_tool_config("TestManagerTool")
    assert config["friendly_name"] == "manager tool"
    assert rbac_service.get_tool_config("NonExistent") is None
