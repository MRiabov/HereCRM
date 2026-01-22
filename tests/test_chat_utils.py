from src.services.chat_utils import format_line_items
from src.uimodels import LineItemInfo

def test_format_line_items():
    items = [
        LineItemInfo(description="Window Clean", quantity=2, unit_price=25.0, total_price=50.0),
        LineItemInfo(description="Gutter Clean", quantity=1, unit_price=30.0, total_price=30.0),
    ]
    
    result = format_line_items(items)
    
    assert "Service    | Qty | Price | Total" in result
    assert "Window Cle.." in result
    assert "2" in result
    assert "25.0" in result
    assert "50.0" in result
    assert "Gutter Cle.." in result
    assert "30.0" in result

def test_format_line_items_empty():
    assert format_line_items([]) == ""
