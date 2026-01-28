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
            # 1. Try to match with catalog
            matched_service = None
            
            # A. LLM Direct Match (Preferred)
            if raw.service_id:
                for s in catalog:
                    if s.id == raw.service_id:
                        matched_service = s
                        break
            
            # B. Fallback to Fuzzy/Token Match (Legacy/Failsafe)
            if not matched_service:
                matched_service = self._find_matching_service(raw.description, catalog)
            
            # Start with raw values
            # Note: LineItemInfo defaults quantity to 1.0 if not provided
            quantity = raw.quantity if raw.quantity is not None else 1.0
            unit_price = raw.unit_price
            total_price = raw.total_price

            explicit_total = raw.total_price is not None

            if matched_service:
                # We found a match in the catalog
                default_price = round(matched_service.default_price, 2)

                if total_price is not None and unit_price is None and quantity == 1.0:
                    # Case: Total price provided, but no unit price or quantity (default 1.0).
                    # Use default price to infer quantity (FR-004).
                    if default_price > 0:
                        # Calculate quantity based on default price
                        raw_qty = total_price / default_price
                        quantity = round(raw_qty, 2)

                        if quantity > 0:
                            # Recalculate unit price to match total exactly
                            # We accept that unit price might deviate slightly from default to satisfy Total = Qty * Unit
                            unit_price = total_price / quantity
                        else:
                            # Edge case: quantity rounds to 0
                            quantity = 1.0
                            unit_price = total_price
                    else:
                        unit_price = 0.0
                        quantity = 1.0 # Fallback
                elif quantity is not None and total_price is None and unit_price is None:
                    # Case: Only quantity provided. Use catalog default price.
                    unit_price = default_price
                    quantity = round(quantity, 2)
                    total_price = round(quantity * unit_price, 2)
                    explicit_total = False
                elif quantity is not None and total_price is not None and unit_price is None:
                    # Case: Quantity and total provided. Calculate unit price.
                    quantity = round(quantity, 2)
                    if quantity > 0:
                        unit_price = total_price / quantity
                    else:
                        unit_price = 0.0
                elif unit_price is not None and quantity is not None and total_price is None:
                    # Case: Unit price and quantity provided. Calculate total.
                    # Use input unit price precision
                    quantity = round(quantity, 2)
                    total_price = round(unit_price * quantity, 2)
                    explicit_total = False
                
                # Fallback for unit price if still None
                if unit_price is None:
                    unit_price = default_price
                
                # If we still don't have total_price
                if total_price is None:
                    quantity = round(quantity, 2)
                    total_price = round(quantity * unit_price, 2)
                    explicit_total = False

                # Final Consistency Check
                final_total = total_price
                if not explicit_total:
                    final_total = round(quantity * unit_price, 2)

                inferred_items.append(
                    LineItem(
                        service_id=matched_service.id,
                        description=matched_service.name, # Use catalog name
                        quantity=round(quantity, 2),
                        unit_price=unit_price,
                        total_price=final_total,
                    )
                )
            else:
                # Ad-hoc item (not in catalog)
                if total_price is not None and quantity is not None and unit_price is None:
                    quantity = round(quantity, 2)
                    if quantity > 0:
                        unit_price = total_price / quantity
                    else:
                        unit_price = 0.0
                elif unit_price is not None and quantity is not None and total_price is None:
                    quantity = round(quantity, 2)
                    total_price = round(unit_price * quantity, 2)
                    explicit_total = False
                
                # Final fallbacks for ad-hoc
                if unit_price is None:
                    unit_price = 0.0
                if quantity is None:
                    quantity = 1.0

                if total_price is None:
                    quantity = round(quantity, 2)
                    total_price = round(quantity * unit_price, 2)
                    explicit_total = False

                final_total = total_price
                if not explicit_total:
                     final_total = round(quantity * unit_price, 2)

                inferred_items.append(
                    LineItem(
                        service_id=None,
                        description=raw.description,
                        quantity=round(quantity, 2),
                        unit_price=unit_price,
                        total_price=final_total,
                    )
                )

        return inferred_items

    def _find_matching_service(self, description: str, catalog: List[Service]) -> Optional[Service]:
        """
        Find the best matching service using token-based fuzzy matching.
        This handles cases like "windows cleaned" matching "Window Cleaning".
        """
        import difflib

        def get_tokens(text: str) -> set[str]:
            return {t.lower() for t in text.split() if len(t) > 1}

        desc_tokens = get_tokens(description)
        if not desc_tokens:
            return None

        best_service = None
        best_score = 0.0

        for service in catalog:
            service_tokens = get_tokens(service.name)
            if not service_tokens:
                continue

            matches = 0
            for s_token in service_tokens:
                # 1. Exact or substring match in description tokens
                if any(s_token in d_token or d_token in s_token for d_token in desc_tokens):
                    matches += 1
                    continue
                
                # 2. Fuzzy match (handles typos or different suffixes like cleaning/cleaned)
                # We check against all description tokens and take the best match for this service token
                token_match_score = 0.0
                for d_token in desc_tokens:
                    ratio = difflib.SequenceMatcher(None, s_token, d_token).ratio()
                    if ratio > token_match_score:
                        token_match_score = ratio
                
                if token_match_score > 0.7:
                    matches += 1

            # Score is percentage of service name tokens found in description
            score = matches / len(service_tokens)
            
            # Prefer longer service names if scores are equal (more specific)
            # But here we just want the highest score.
            if score > best_score:
                best_score = score
                best_service = service
            elif score == best_score and best_score > 0:
                # Tie-breaker: choose the one with better overall string similarity
                current_ratio = difflib.SequenceMatcher(None, service.name.lower(), description.lower()).ratio()
                best_ratio = difflib.SequenceMatcher(None, best_service.name.lower(), description.lower()).ratio()
                if current_ratio > best_ratio:
                    best_service = service

        # Threshold: Require at least 50% of the service name to be found/matched
        if best_score >= 0.5:
            return best_service
            
        return None
