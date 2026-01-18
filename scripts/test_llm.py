import asyncio
import os
import logging
import sys

# Configure logging to see errors from llm_client
root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

from src.llm_client import parser

async def test_llm():
    try:
        print("Starting parse...")
        result = await parser.parse("Hello")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Caught Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_llm())
