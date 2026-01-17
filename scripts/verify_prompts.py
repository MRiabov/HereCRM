import asyncio
import argparse
import json
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import AsyncOpenAI
from src.config import settings
from src.llm_client import LLMParser
from src.uimodels import (
    AddJobTool,
    AddLeadTool,
    EditCustomerTool,
    ScheduleJobTool,
    AddRequestTool,
    SearchTool,
    UpdateSettingsTool,
    ConvertRequestTool,
    HelpTool,
    GetPipelineTool,
    AddServiceTool,
    EditServiceTool,
    DeleteServiceTool,
    ListServicesTool,
    ExitSettingsTool,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATA_FILE = "tests/data/llm_verification_set.json"

async def generate_prompts(count: int):
    logger.info(f"Generating {count} prompts using LLM...")
    
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )

    prompts_per_batch = 10
    batches = (count + prompts_per_batch - 1) // prompts_per_batch
    
    all_cases = []
    
    tools_schema = [
        AddJobTool.schema(),
        AddLeadTool.schema(),
        EditCustomerTool.schema(),
        ScheduleJobTool.schema(),
        AddRequestTool.schema(),
        SearchTool.schema(),
        UpdateSettingsTool.schema(),
        ConvertRequestTool.schema(),
        HelpTool.schema(),
        GetPipelineTool.schema(),
        AddServiceTool.schema(),
        EditServiceTool.schema(),
        DeleteServiceTool.schema(),
        ListServicesTool.schema(),
        ExitSettingsTool.schema(),
    ]

    system_prompt = f"""
You are a QA Engineer generating test cases for a CRM LLM Agent.
Your task is to generate realistic user prompts and the expected tool call that the agent should make.

The agent has access to the following tools (Pydantic schemas):
{json.dumps(tools_schema, indent=2)}

Generate {prompts_per_batch} diverse test cases.
Include a mix of:
1. Clear, professional commands.
2. Short, casual, slang-filled messages.
3. Messages with typos or grammatical errors.
4. Complex requests with multiple parameters.
5. Edge cases (e.g., weird formatting, extra whitespace).

Format the output as a valid JSON object with a single key "test_cases" which is a list of objects.
Each object in "test_cases" must have:
- "user_input": The string the user types.
- "expected_tool": The name of the tool class (e.g., "AddJobTool").
- "expected_args": A dictionary of arguments for the tool.
- "system_time": Optional. If the prompt relies on relative time (e.g. "tomorrow"), provide a ISO timestamp context (e.g. "2025-06-01T10:00:00").

Example output format:
{{
  "test_cases": [
      {{
        "user_input": "schedule job for john tomorrow at 2pm",
        "expected_tool": "ScheduleJobTool",
        "expected_args": {{ "customer_query": "john", "time": "tomorrow at 2pm", "iso_time": "2025-06-02T14:00:00" }},
        "system_time": "2025-06-01T10:00:00"
      }}
  ]
}}
DO NOT wrap in markdown code blocks.
"""

    # Clear existing dump file
    JSONL_FILE = DATA_FILE.replace(".json", ".jsonl")
    if os.path.exists(JSONL_FILE):
        os.remove(JSONL_FILE)
        
    # Create batches
    batch_indices = list(range(batches))
    
    # Semaphore to limit concurrency
    sem = asyncio.Semaphore(5) 

    async def generate_batch(batch_idx):
        async with sem:
            logger.info(f"Starting batch {batch_idx+1}/{batches}...")
            try:
                response = await client.chat.completions.create(
                    model=settings.openrouter_model,
                    messages=[{"role": "system", "content": system_prompt}],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                
                try:
                    data = json.loads(content)
                    batch_cases = data.get("test_cases", [])
                    
                    if not batch_cases and isinstance(data, list):
                        batch_cases = data

                    if not batch_cases:
                        logger.warning(f"Batch {batch_idx+1}: Could not find 'test_cases' list")
                        return []
                    
                    # Append strictly to JSONL
                    with open(JSONL_FILE, "a") as f:
                        for case in batch_cases:
                            f.write(json.dumps(case) + "\n")
                            
                    logger.info(f"Batch {batch_idx+1} complete: {len(batch_cases)} cases saved.")
                    return batch_cases
                except json.JSONDecodeError:
                    logger.error(f"Batch {batch_idx+1}: Failed to parse JSON")
                    return []
                
            except Exception as e:
                logger.error(f"Error generating batch {batch_idx+1}: {e}")
                return []

    await asyncio.gather(*(generate_batch(i) for i in batch_indices))
            
    # Convert JSONL to JSON final
    final_cases = []
    if os.path.exists(JSONL_FILE):
        with open(JSONL_FILE, "r") as f:
            for line in f:
                if line.strip():
                    final_cases.append(json.loads(line))
    
    # Save to file
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(final_cases, f, indent=2)
    
    logger.info(f"Saved {len(final_cases)} test cases to {DATA_FILE}")

async def verify_prompts():
    test_cases = []
    JSONL_FILE = DATA_FILE.replace(".json", ".jsonl")
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            test_cases = json.load(f)
    elif os.path.exists(JSONL_FILE):
        logger.info(f"JSON file missing, reading from {JSONL_FILE}")
        with open(JSONL_FILE, "r") as f:
            for line in f:
                if line.strip():
                    test_cases.append(json.loads(line))
    else:
        logger.error(f"Data file {DATA_FILE} (or .jsonl) not found. Run with --generate first.")
        return

    logger.info(f"Verifying {len(test_cases)} test cases in parallel...")
    
    # Filter valid cases
    valid_cases = []
    for i, case in enumerate(test_cases):
        if isinstance(case, dict):
            valid_cases.append(case)
        else:
             logger.warning(f"Skipping malformed test case #{i}: {case} (type: {type(case)})")
    
    test_cases = valid_cases
    parser = LLMParser()
    sem = asyncio.Semaphore(10)
    
    async def verify_case(case):
        async with sem:
            user_input = case.get("user_input")
            expected_tool_name = case.get("expected_tool")
            expected_args = case.get("expected_args", {})
            system_time = case.get("system_time")
            
            # Determine strict or settings parse
            is_settings = expected_tool_name in [
                "AddServiceTool", "EditServiceTool", "DeleteServiceTool", "ListServicesTool", "ExitSettingsTool"
            ]
            
            failure_reason = None
            actual_tool = None
            mismatch_warnings = []
            
            try:
                if is_settings:
                    result = await parser.parse_settings(user_input)
                else:
                    result = await parser.parse(user_input, system_time=system_time)
                
                # Check result
                if result is None:
                    failure_reason = "No tool call"
                    return {"passed": False, "case": case, "reason": failure_reason, "actual": None}
                    
                actual_tool_name = result.__class__.__name__
                actual_tool = actual_tool_name
                
                if actual_tool_name != expected_tool_name:
                    failure_reason = "Wrong tool class"
                    return {"passed": False, "case": case, "reason": failure_reason, "actual": actual_tool_name}
                
                if hasattr(result, "dict"):
                     actual_args = result.dict(exclude_none=True)
                else:
                     actual_args = {}
                
                for key, val in expected_args.items():
                    if key not in actual_args:
                        mismatch_warnings.append(f"Missing arg {key}")
                    elif str(actual_args[key]) != str(val):
                        # Allow some flexibility for iso_time
                        if key == "iso_time":
                            continue
                        if isinstance(val, (int, float)) and isinstance(actual_args[key], (int, float)):
                             if abs(val - actual_args[key]) > 0.1:
                                 mismatch_warnings.append(f"Arg {key} mismatch: exp {val} vs act {actual_args[key]}")
                        else:
                            mismatch_warnings.append(f"Arg {key} mismatch: exp {val} vs act {actual_args[key]}")
                
                if mismatch_warnings:
                    return {"passed": True, "case": case, "warnings": mismatch_warnings}
                
                return {"passed": True, "case": case}

            except Exception as e:
                return {"passed": False, "case": case, "reason": f"Exception: {e}", "actual": "Error"}

    results = await asyncio.gather(*(verify_case(case) for case in test_cases))
    
    passed = len([r for r in results if r["passed"]])
    failed = len(test_cases) - passed
    failed_cases = [r for r in results if not r["passed"]]
    warn_cases = [r for r in results if r.get("warnings")]

    success_rate = (passed / len(test_cases)) * 100 if test_cases else 0
    
    report = []
    report.append("="*30)
    report.append(f"VERIFICATION COMPLETE")
    report.append(f"Total: {len(test_cases)}")
    report.append(f"Passed: {passed}")
    report.append(f"Failed: {failed}")
    report.append(f"Success Rate: {success_rate:.2f}%")
    report.append("="*30)
    
    if failed_cases:
        report.append("\nFAILED CASES SAMPLE (Top 10):")
        for fc in failed_cases[:10]:
             report.append(f"- Input: {fc['case'].get('user_input')}")
             report.append(f"  Exp: {fc['case'].get('expected_tool')}")
             report.append(f"  Reason: {fc['reason']}")
             if fc.get("actual"):
                 report.append(f"  Act: {fc['actual']}")

    if warn_cases:
        report.append("\nWARNING SAMPLE (Tool Matched but Args Mismatch) (Top 5):")
        for wc in warn_cases[:5]:
            report.append(f"- Input: {wc['case'].get('user_input')}")
            report.append(f"  Warnings: {wc['warnings']}")

    print("\n".join(report))
    
    # Save report
    with open("verification_report.txt", "w") as f:
        f.write("\n".join(report))
    logger.info("Report saved to verification_report.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true", help="Generate prompts")
    parser.add_argument("--count", type=int, default=50, help="Number of prompts to generate")
    parser.add_argument("--verify", action="store_true", help="Verify prompts")
    
    args = parser.parse_args()
    
    if args.generate:
        asyncio.run(generate_prompts(args.count))
    if args.verify:
        asyncio.run(verify_prompts())
    if not args.generate and not args.verify:
        parser.print_help()
