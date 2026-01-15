from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Service, LineItem
from src.uimodels import LineItemInfo


class InferenceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def infer_line_items(
        self, business_id: int, raw_items: List[LineItemInfo]
    ) -> List[LineItem]:
        """
        Reconcile raw line items from LLM with the service catalog and infer missing values.
        """
        # Fetch all services for the business for matching
        stmt = select(Service).where(Service.business_id == business_id)
        result = await self.session.execute(stmt)
        catalog = list(result.scalars().all())

        inferred_items = []
        for raw in raw_items:
            # Try to match with catalog
            matched_service = self._find_matching_service(raw.description, catalog)
            
            quantity = raw.quantity or 1.0
            unit_price = raw.unit_price
            total_price = raw.total_price

            if matched_service:
                # We found a match in the catalog
                default_price = round(matched_service.default_price, 2)

                if total_price is not None and unit_price is None and quantity == 1.0:
                    # Case: Total price provided, but no unit price or quantity. 
                    # Use default price to infer quantity.
                    if default_price > 0:
                        unit_price = default_price
                        quantity = round(total_price / unit_price, 2)
                        # Re-calculate total from rounded quantity to ensure consistency
                        total_price = round(quantity * unit_price, 2)
                    else:
                        unit_price = 0.0
                        quantity = 1.0 # Fallback
                        total_price = round(total_price, 2)
                elif quantity is not None and total_price is None and unit_price is None:
                    # Case: Only quantity provided. Use catalog default price.
                    unit_price = default_price
                    quantity = round(quantity, 2)
                    total_price = round(quantity * unit_price, 2)
                elif quantity is not None and total_price is not None and unit_price is None:
                    # Case: Quantity and total provided. Calculate unit price.
                    quantity = round(quantity, 2)
                    if quantity > 0:
                        unit_price = round(total_price / quantity, 2)
                        # Re-adjust total to match rounded values
                        total_price = round(quantity * unit_price, 2)
                    else:
                        unit_price = 0.0
                        total_price = round(total_price, 2)
                elif unit_price is not None and quantity is not None and total_price is None:
                    # Case: Unit price and quantity provided. Calculate total.
                    unit_price = round(unit_price, 2)
                    quantity = round(quantity, 2)
                    total_price = round(unit_price * quantity, 2)
                
                # Fallback for unit price if still None
                if unit_price is None:
                    unit_price = default_price
                
                if total_price is None:
                    quantity = round(quantity, 2)
                    unit_price = round(unit_price, 2)
                    total_price = round(quantity * unit_price, 2)

                inferred_items.append(
                    LineItem(
                        service_id=matched_service.id,
                        description=matched_service.name, # Use catalog name
                        quantity=round(quantity, 2),
                        unit_price=round(unit_price, 2),
                        total_price=round(total_price, 2),
                    )
                )
            else:
                # Ad-hoc item (not in catalog)
                if total_price is not None and quantity is not None and unit_price is None:
                    quantity = round(quantity, 2)
                    if quantity > 0:
                        unit_price = round(total_price / quantity, 2)
                        total_price = round(quantity * unit_price, 2)
                    else:
                        unit_price = 0.0
                        total_price = round(total_price, 2)
                elif unit_price is not None and quantity is not None and total_price is None:
                    unit_price = round(unit_price, 2)
                    quantity = round(quantity, 2)
                    total_price = round(unit_price * quantity, 2)
                
                # Final fallbacks for ad-hoc
                if unit_price is None:
                    unit_price = 0.0
                if total_price is None:
                    quantity = round(quantity, 2)
                    unit_price = round(unit_price, 2)
                    total_price = round(quantity * unit_price, 2)

                inferred_items.append(
                    LineItem(
                        service_id=None,
                        description=raw.description,
                        quantity=round(quantity, 2),
                        unit_price=round(unit_price, 2),
                        total_price=round(total_price, 2),
                    )
                )

        return inferred_items

    def _find_matching_service(self, description: str, catalog: List[Service]) -> Optional[Service]:
        """Simple fuzzy match for service description against catalog names."""
        desc_lower = description.lower()
        for service in catalog:
            if service.name.lower() in desc_lower or desc_lower in service.name.lower():
                return service
        return None
