from typing import List, Any
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

def format_line_items(line_items: List[Any]) -> str:
    """
    Format a list of line items into a table-like string for WhatsApp.
    Example:
    `Service    | Qty | Total`
    `-----------|-----|------`
    `Win Clean  |  1  | $50.0`
    """
    if not line_items:
        return ""

    # Header
    header = "`Service    | Qty | Price | Total`"
    sep = "`------------|-----|-------|------`"
    lines = [header, sep]

    for item in line_items:
        # Extract name/description from various possible attributes
        # LineItemInfo has 'description', LineItem model has 'service_name' or 'description'
        name = (
            getattr(item, "description", None) 
            or getattr(item, "service_name", None) 
            or getattr(item, "name", "Item")
        )
        qty = getattr(item, "quantity", 1)
        price = getattr(item, "unit_price", 0)
        total = getattr(item, "total_price", qty * price)

        # Truncate name to 10 chars
        name_p = (name[:10] + "..") if len(name) > 10 else name.ljust(12)
        qty_p = str(qty).center(5)
        price_p = f"{price:.1f}".center(7)
        total_p = f"{total:.1f}".center(6)

        lines.append(f"`{name_p}|{qty_p}|{price_p}|{total_p}`")

    return "\n".join(lines)
