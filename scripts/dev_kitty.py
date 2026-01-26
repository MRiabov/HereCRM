#!/usr/bin/env python3
import os
import re
import subprocess
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

def get_specs(specs_dir):
    specs = []
    if not specs_dir.exists():
        return specs
    
    for item in sorted(specs_dir.iterdir()):
        if item.is_dir():
            match = re.match(r"^(\d+)-(.+)$", item.name)
            if match:
                number = match.group(1)
                name = match.group(2)
                specs.append({
                    "number": number,
                    "name": name,
                    "full_name": item.name,
                    "path": item
                })
    return specs

def parse_activity_log(content):
    """
    Parses the ## Activity Log section to find the latest status.
    Returns (status, timestamp_epoch) or (None, None).
    """
    log_pattern = re.compile(r"## Activity Log\s*(.*)", re.DOTALL)
    log_match = log_pattern.search(content)
    
    if not log_match:
        return None, None
    
    log_content = log_match.group(1)
    
    # Pattern to extract timestamp and lane from lines like:
    # - 2026-01-20T17:58:00Z – Antigravity – ... – lane=done – ...
    # Note: The separator might be hyphens or en-dashes/em-dashes.
    # We look for the last occurrence.
    
    entries = []
    for line in log_content.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        
        # Extract timestamp (ISO8601ish)
        ts_match = re.match(r"- (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?)", line)
        lane_match = re.search(r"lane=([a-zA-Z0-9_]+)", line)
        
        if ts_match and lane_match:
            try:
                # Handle 'Z' if present, otherwise assume UTC
                ts_str = ts_match.group(1).replace('Z', '+00:00')
                if not ts_str.endswith('+00:00') and not '+' in ts_str[-6:]:
                     ts_str += '+00:00'
                
                dt = datetime.fromisoformat(ts_str)
                timestamp = dt.timestamp()
                lane = lane_match.group(1).lower()
                entries.append((timestamp, lane))
            except ValueError:
                continue

    if not entries:
        return None, None
        
    # Sort by timestamp, get the latest
    entries.sort(key=lambda x: x[0])
    return entries[-1]

def get_tasks(spec_path):
    tasks_dir = spec_path / "tasks"
    tasks = []
    if not tasks_dir.exists():
        return tasks
    
    for item in sorted(tasks_dir.glob("*.md")):
        if item.name == "README.md":
            continue
            
        try:
            content = item.read_text()
            
            # 1. Try Activity Log first
            lane, timestamp = parse_activity_log(content)
            source = "log"
            
            # 2. Fallback to YAML front matter if log not found
            if not lane:
                front_matter_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
                if front_matter_match:
                    front_matter = front_matter_match.group(1)
                    lane_match = re.search(r"^lane:\s*[\"']?([a-zA-Z0-9_]+)[\"']?", front_matter, re.MULTILINE)
                    if lane_match:
                        lane = lane_match.group(1).lower()
                        # Use file modification time as fallback timestamp
                        timestamp = item.stat().st_mtime
                        source = "front_matter"
            
            if lane:
                tasks.append({
                    "file_path": item,
                    "file_name": item.name,
                    "lane": lane,
                    "timestamp": timestamp,
                    "source": source
                })

        except Exception as e:
            print(f"Warning: Failed to parse {item}: {e}")
            
    return tasks

def main():
    parser = argparse.ArgumentParser(description="Batch run gemini spec-kitty tasks based on task files.")
    parser.add_argument("--execute", "-x", action="store_true", help="Execute the commands. Default is dry-run.")
    parser.add_argument("--filter", "-f", help="Filter specs by number or name (partial match).")
    parser.add_argument("--force-action", choices=["implement", "review"], help="Force specific action.")
    
    args = parser.parse_args()

    # Setup paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    specs_dir = project_root / "kitty-specs"

    if not specs_dir.exists():
        print(f"Error: Directory not found: {specs_dir}")
        sys.exit(1)

    specs = get_specs(specs_dir)
    commands = []

    print(f"{ 'SPEC / TASK':<50} | { 'STATUS':<20} | {'ACTION'}")
    print("-" * 85)

    current_time = time.time()

    for spec in specs:
        # Filter
        if args.filter:
            if args.filter not in spec["number"] and args.filter.lower() not in spec["name"].lower():
                continue

        tasks = get_tasks(spec["path"])
        
        for task in tasks:
            status = task["lane"]
            action = None
            reason = ""

            if args.force_action:
                action = args.force_action
                reason = "Forced"
            else:
                if status == "for_review":
                    action = "review"
                elif status == "planned":
                    action = "implement"
                elif status == "doing":
                    # Check if started > 15 mins ago (900 seconds)
                    time_diff = current_time - task["timestamp"]
                    if time_diff > 900:
                        action = "implement"
                        reason = f"Stalled ({int(time_diff/60)}m)"
                    else:
                        reason = f"Active ({int(time_diff/60)}m)"
                elif status == "done":
                    # Skip
                    pass
                else:
                    # Unknown status, maybe approved?
                    pass

            if action:
                cmd = [
                    "gemini", 
                    "--yolo", 
                    "--prompt", 
                    f"@spec-kitty {action} {spec['name']} {spec['number']}"
                ]
                commands.append(cmd)
                
                display_name = f"{spec['number']}/{task['file_name']}"
                status_display = f"{status.upper()}"
                if reason:
                    status_display += f" ({reason})"
                
                print(f"{display_name:<50} | {status_display:<20} | {action.upper()}")

    if not commands:
        print("\nNo actionable tasks found.")
        return

    if args.execute:
        print("\nExecuting commands...")
        for cmd in commands:
            cmd_str = " ".join(f"'{c}'" if " " in c else c for c in cmd)
            print(f"\nRunning: {cmd_str}")
            try:
                subprocess.run(cmd, check=True)
            except FileNotFoundError:
                print("Error: 'gemini' command not found. Make sure it is installed and in your PATH.")
                break
            except subprocess.CalledProcessError as e:
                print(f"Error running command: {e}")
            except KeyboardInterrupt:
                print("\nAborted by user.")
                break
    else:
        print("\nDry run complete. Use --execute (-x) to run.")

if __name__ == "__main__":
    main()