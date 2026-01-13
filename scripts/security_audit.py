import ast
import os
import sys


def audit_repositories(file_path):
    with open(file_path, "r") as f:
        tree = ast.parse(f.read())

    errors = []

    # We are looking for classes that end with 'Repository'
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # UserRepository and ConversationStateRepository are global by design (phone-based)
            if node.name in ["UserRepository", "ConversationStateRepository"]:
                continue

            # For other repositories, check async methods (queries)
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef):
                    # Methods to exclude from mandatory business_id check
                    # (e.g., __init__, or global lookups if any)
                    if item.name.startswith("__") or item.name.endswith("_global"):
                        continue

                    # Check if 'business_id' is an argument
                    arg_names = [arg.arg for arg in item.args.args]
                    if "business_id" not in arg_names:
                        errors.append(
                            f"Class {node.name}, Method {item.name}: Missing 'business_id' argument"
                        )
                        continue

                    # Check if 'business_id' is used in the body (simplified check)
                    used = False
                    for subnode in ast.walk(item):
                        if (
                            isinstance(subnode, ast.Name)
                            and subnode.id == "business_id"
                        ):
                            used = True
                            break

                    if not used:
                        errors.append(
                            f"Class {node.name}, Method {item.name}: 'business_id' argument provided but NOT USED in query"
                        )

    return errors


if __name__ == "__main__":
    repo_file = "/home/maksym/Work/proj/HereCRM/.worktrees/001-whatsapp-ai-crm/src/repositories.py"
    if not os.path.exists(repo_file):
        print(f"Error: {repo_file} not found.")
        sys.exit(1)

    print(f"Auditing {repo_file} for multi-tenant scoping...")
    audit_errors = audit_repositories(repo_file)

    if audit_errors:
        print("\n[!] SECURITY AUDIT FAILED:")
        for err in audit_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print(
            "\n[✓] SECURITY AUDIT PASSED: All repository methods are correctly scoped."
        )
        sys.exit(0)
