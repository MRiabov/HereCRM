import yaml
import sys

try:
    with open("/home/maksym/Work/proj/HereCRM/src/assets/prompts.yaml", "r") as f:
        data = yaml.safe_load(f)
    print("YAML is valid.")
    # check for tool_descriptions key
    if "tool_descriptions" not in data:
        print("Warning: tool_descriptions key missing!")
    else:
        print(f"Found {len(data['tool_descriptions'])} tool descriptions.")
except yaml.YAMLError as exc:
    print(f"YAML Error: {exc}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
