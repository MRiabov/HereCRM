from typing import List
from src.models import Service

def format_service_list(services: List[Service]) -> str:
    """
    Format a list of services into a readable string for WhatsApp.
    Example:
    1. Window Clean - $50.00
    2. Gutter Clean - $30.00
    """
    if not services:
        return "No services found."
        
    lines = []
    for svc in services:
        price_str = f"${svc.default_price:.2f}"
        lines.append(f"{svc.id}. *{svc.name}* — {price_str}")
        
    return "\n".join(lines)
