import os
import re

def fix_tests(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py") and file.startswith("test_"):
                path = os.path.join(root, file)
                with open(path, 'r') as f:
                    content = f.read()
                
                # 1. Fix ToolExecutor instantiation
                # Look for ToolExecutor(..., phone, template) and try to inject user_id/user.id
                # Pattern: ToolExecutor(..., [anything], [anything])
                # This is hard to do with regex perfectly if we don't know the variable names.
                # But often it's: ToolExecutor(db_session, business_id, user.phone_number, mock_template_service)
                
                # Replace ToolExecutor(session, biz_id, phone, template) with ToolExecutor(session, biz_id, user_id, phone, template)
                # We'll try to find common patterns.
                
                # 2. Fix ConversationState instantiation
                content = content.replace("ConversationState(phone_number=", "ConversationState(user_id=")
                
                # 3. Fix ConversationState queries
                content = content.replace("ConversationState.phone_number ==", "ConversationState.user_id ==")
                
                # Specific common pattern in tests:
                # user.phone_number as 3rd arg in ToolExecutor
                content = re.sub(
                    r"ToolExecutor\(([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\)",
                    r"ToolExecutor(\1, \2, user.id, \3, \4)", 
                    content
                )
                # Wait, what if the 3rd arg isn't phone? 
                # In most tests it is: db_session, business_id, user.phone_number, template
                
                with open(path, 'w') as f:
                    f.write(content)

if __name__ == "__main__":
    fix_tests("tests")
