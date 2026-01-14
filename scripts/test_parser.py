import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def test_parser():
    from src.llm_client import LLMParser

    parser = LLMParser()

    print("Testing 'Add lead: John' (Expected: Lead)")
    tool2 = await parser.parse("Add lead: John")
    print(f"Tool 2: {tool2}")


if __name__ == "__main__":
    asyncio.run(test_parser())
