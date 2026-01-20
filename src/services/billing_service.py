import asyncio
import os
import yaml
import stripe
import logging
from src.repositories import BusinessRepository
from sqlalchemy.ext.asyncio import AsyncSession

class BillingService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.business_repo = BusinessRepository(session)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Stripe
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe_key:
            self.logger.warning("STRIPE_SECRET_KEY not set. Billing operations will fail.")
        stripe.api_key = stripe_key
        
        # Load billing config
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "billing_config.yaml")
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load billing config: {e}")
            self.config = {"products": {}, "addons": []}

    async def get_billing_status(self, business_id: int) -> dict:
        """Fetch formatted subscription info for a business."""
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            return {"error": "Business not found"}
        
        return {
            "status": business.subscription_status,
            "seat_limit": business.seat_limit,
            "active_addons": business.active_addons,
            "stripe_customer_id": business.stripe_customer_id
        }

    async def create_checkout_session(self, business_id: int, price_id: str, success_url: str, cancel_url: str) -> str:
        """Creates a new subscription checkout session."""
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            raise ValueError("Business not found")

        params = {
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "business_id": str(business_id)
            },
        }

        # If we have a customer ID, attach it
        if business.stripe_customer_id:
            params["customer"] = business.stripe_customer_id

        try:
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                **params
            )
            return session.url
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe session creation failed for business {business_id}: {e}")
            raise

    async def create_upgrade_link(self, business_id: int, item_type: str, item_id: str, success_url: str, cancel_url: str) -> dict:
        """Creates an upgrade link with proration if possible."""
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            raise ValueError("Business not found")

        # Find the price_id from config
        price_id = None
        item_name = item_id or item_type
        
        if item_type == "seat":
            price_id = self.config.get("products", {}).get("seat", {}).get("price_id")
            item_name = "Additional Seat"
        elif item_type == "addon":
            for addon in self.config.get("addons", []):
                if addon.get("id") == item_id:
                    price_id = addon.get("price_id")
                    item_name = addon.get("name", item_id)
                    break
        
        if not price_id:
            raise ValueError(f"Invalid item: {item_type}/{item_id}")

        self.logger.info(f"Creating upgrade link for business {business_id}, item {item_name}")
        
        try:
            url = await self.create_checkout_session(business_id, price_id, success_url, cancel_url)
            return {
                "url": url,
                "description": f"Upgrade: {item_name}"
            }
        except Exception as e:
            self.logger.error(f"Upgrade link generation failed: {e}")
            raise

