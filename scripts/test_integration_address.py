import asyncio
from unittest.mock import AsyncMock, MagicMock
from src.tool_executor import ToolExecutor
from src.uimodels import AddLeadTool
from src.services.template_service import TemplateService

async def test_lead_address_resolution():
    # Mock dependencies
    session = AsyncMock()
    business_id = 1
    user_id = 1
    user_phone = "+123456789"
    template_service = TemplateService()
    
    # Mock Repository
    mock_biz = MagicMock(default_city=None, default_country=None)
    session.get = AsyncMock(return_value=mock_biz)
    executor = ToolExecutor(session, business_id, user_id, user_phone, template_service)
    executor.customer_repo = AsyncMock()
    executor.customer_repo.get_by_name.return_value = None
    executor.customer_repo.get_by_phone.return_value = None
    executor.user_repo = AsyncMock()
    executor.user_repo.get_by_id.return_value = MagicMock(role="owner", preferences={})
    
    # Tool call
    tool = AddLeadTool(name="John Doe", location="high street 34, Dublin")
    
    print(f"Executing AddLeadTool with location: {tool.location}")
    response, _ = await executor.execute(tool)
    
    print("\nResponse from ToolExecutor:")
    print(response)
    
    if "D08 CX34" in response or "Dublin" in response:
        print("\nSUCCESS: Resolved address found in AddLeadTool response.")
    else:
        print("\nFAILURE: Resolved address NOT found in AddLeadTool response.")
    
    # Test with Defaults
    print("\n--- Testing with Defaults (Dublin, Ireland) ---")
    executor.user_repo.get_by_id.return_value = MagicMock(
        role="owner", 
        preferences={"default_city": "Dublin", "default_country": "Ireland"}
    )
    
    # Case 1: Partial address, should append Dublin
    tool2 = AddLeadTool(name="Jane Doe", location="high street 34")
    print(f"Executing AddLeadTool with location: {tool2.location}")
    response2, _ = await executor.execute(tool2)
    print(response2)
    if "Dublin" in response2:
        print("SUCCESS: Default city Dublin appended.")
    else:
        print("FAILURE: Default city Dublin NOT found.")

    # Case 2: Explicit override in tool.location, should NOT append Dublin
    tool3 = AddLeadTool(name="Bob Smith", location="high street 34, Waterford")
    print(f"\nExecuting AddLeadTool with location: {tool3.location}")
    response3, _ = await executor.execute(tool3)
    print(response3)
    # Note: Waterford might find Waterford in US if Ireland not appended, but Dublin should NOT be there.
    if "Dublin" not in response3:
        print("SUCCESS: Default city Dublin NOT appended.")
    else:
        print("FAILURE: Default city Dublin STILL appended.")

    # Case 3: Explicit city in tool.city, location is just street
    tool4 = AddLeadTool(name="Alice Brown", location="high street 34", city="Waterford", country="Ireland")
    print("\nExecuting AddLeadTool with city='Waterford', location='high street 34'")
    response4, _ = await executor.execute(tool4)
    print(response4)
    if "Waterford" in response4 and "Ireland" in response4 and "Dublin" not in response4:
        print("SUCCESS: Explicit city Waterford used, Dublin ignored.")
    else:
        print("FAILURE: Explicit city/country handling failed.")

if __name__ == "__main__":
    asyncio.run(test_lead_address_resolution())
