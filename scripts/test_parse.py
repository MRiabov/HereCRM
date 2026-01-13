import asyncio
import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.llm_client import LLMParser  # noqa: E402
from src.config import settings  # noqa: E402


async def main():
    if not settings.google_api_key or settings.google_api_key == "dummy":
        print(
            "Warning: GOOGLE_API_KEY is not set correctly. This will fail if hitting the real API."
        )
        print("Set it via export GOOGLE_API_KEY=your_key")

    parser = LLMParser()

    test_inputs = [
        "Add a job for John Doe: fix the leaky faucet in the kitchen, price is $150",
        "Schedule John Doe for tomorrow at 2pm",
        "Customer is happy with the work",
        "Search for leaky faucet",
        "Update confirm_by_default to True",
    ]

    for text in test_inputs:
        print(f"\nInput: {text}")
        try:
            result = await parser.parse(text)
            print(f"Parsed Tool: {result}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
