import logging
from typing import List, Dict, Optional
from src.models import Business, Customer

logger = logging.getLogger(__name__)

class TaxCalculator:
    """
    Service to calculate taxes for quotes and invoices.
    Ideally integrates with Stripe Tax, but uses a simplified logic for now.
    """

    def __init__(self, default_tax_rate: float = 0.0):
        self.default_tax_rate = default_tax_rate

    def calculate_quote_tax(
        self,
        lines: List[Dict],
        business: Business,
        customer: Optional[Customer] = None
    ) -> Dict[str, float]:
        """
        Calculates subtotal, tax, and total based on business settings.

        Args:
            lines: List of dicts with 'quantity', 'unit_price' (and 'tax_behavior' if supported)
            business: The business entity with tax settings.
            customer: The customer entity (for location-based tax lookup).

        Returns:
            Dict with keys: subtotal, tax_amount, tax_rate, total_amount
        """

        # Determine tax rate
        # TODO: Integrate with Stripe Tax API here using customer location
        # Priority: Business preference -> Default calculator rate
        tax_rate = business.default_tax_rate if business.default_tax_rate is not None else self.default_tax_rate

        # Calculate raw total from lines
        raw_total = 0.0
        for line in lines:
            qty = line.get("quantity", 0)
            price = line.get("unit_price", 0)
            raw_total += qty * price

        if business.workflow_tax_inclusive:
            # Price includes tax
            # Total = Subtotal + Tax
            # Tax = Total - (Total / (1 + Rate))
            total_amount = raw_total
            subtotal = total_amount / (1 + tax_rate)
            tax_amount = total_amount - subtotal
        else:
            # Tax is added on top
            subtotal = raw_total
            tax_amount = subtotal * tax_rate
            total_amount = subtotal + tax_amount

        return {
            "subtotal": round(subtotal, 2),
            "tax_amount": round(tax_amount, 2),
            "tax_rate": tax_rate,
            "total_amount": round(total_amount, 2)
        }

# Global instance
tax_calculator = TaxCalculator()
