import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from services.template_service import TemplateService


def verify_templates():
    ts = TemplateService()

    print("--- Verifying Quoting ---")
    quote_msg = ts.render(
        "job_added",
        category="Quote",
        name="John Doe",
        location="",
        price_info=" (Total: 100)",
    )
    print(f"Quote Msg: {quote_msg}")

    print("\n--- Verifying Routing ---")
    preview = ts.render("autoroute_preview", date="2024-01-01", routes="[Routes Body]")
    print(f"Preview Header: {preview.splitlines()[0]}")

    applied = ts.render("autoroute_applied", count=5)
    print(f"Applied: {applied}")

    print("\n--- DONE ---")


if __name__ == "__main__":
    verify_templates()
