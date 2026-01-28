
import sys
import asyncio
from src.models import MessageTriggerSource, EntityType, MessageType, CampaignService
from src.services.campaign_service import CampaignService as CS

def verify():
    print("Verifying Enum refactoring...")
    
    # Check MessageTriggerSource
    try:
        print(f"MessageTriggerSource keys: {[e.name for e in MessageTriggerSource]}")
        assert "CAMPAIGN" in MessageTriggerSource.__members__
        assert "MANUAL" in MessageTriggerSource.__members__
        assert MessageTriggerSource.CAMPAIGN == "CAMPAIGN"
        print("MessageTriggerSource OK")
    except Exception as e:
        print(f"MessageTriggerSource Failed: {e}")
        return False
        
    # Check EntityType
    try:
        assert EntityType.CUSTOMER == "customer"
        print("EntityType OK")
    except Exception as e:
        print(f"EntityType Failed: {e}")
        return False
        
    print("Verification Successful")
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)
