import asyncio
import os
import yaml
import stripe
import logging
from src.repositories import BusinessRepository
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import Business

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


    async def process_webhook(self, event: dict):
        """Process incoming Stripe webhook events."""
        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        self.logger.info(f"Processing webhook event: {event_type}")

        if event_type == "checkout.session.completed":
            await self._handle_checkout_completed(data)
        elif event_type == "customer.subscription.updated":
            await self._handle_subscription_updated(data)
        elif event_type == "customer.subscription.deleted":
             await self._handle_subscription_deleted(data)

    async def _handle_checkout_completed(self, session: dict):
        metadata = session.get("metadata", {})
        business_id = metadata.get("business_id")
        
        if not business_id:
            self.logger.warning(f"Webhook {session.get('id')} missing business_id metadata")
            return
            
        business_id = int(business_id)
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            self.logger.error(f"Business {business_id} not found for webhook {session.get('id')}")
            return
            
        business.stripe_customer_id = customer_id
        business.stripe_subscription_id = subscription_id
        business.subscription_status = "active"
        
        await self.session.commit()
        self.logger.info(f"Linked business {business_id} to customer {customer_id}")

    async def _handle_subscription_updated(self, subscription: dict):
        customer_id = subscription.get("customer")
        metadata = subscription.get("metadata", {})
        business_id = metadata.get("business_id")
        
        business = None
        if business_id:
             business = await self.business_repo.get_by_id_global(int(business_id))
        
        if not business and customer_id:
             # Find by customer_id
             result = await self.session.execute(select(Business).where(Business.stripe_customer_id == customer_id))
             business = result.scalar_one_or_none()
             
        if not business:
            self.logger.error(f"Business not found for subscription {subscription.get('id')}")
            return

        status = subscription.get("status")
        business.subscription_status = status
        
        # Calculate seats and addons
        items = subscription.get("items", {}).get("data", [])
        
        seat_price_id = self.config.get("products", {}).get("seat", {}).get("price_id")
        addon_price_map = {}
        for addon in self.config.get("addons", []):
            if addon.get("price_id"):
                 addon_price_map[addon.get("price_id")] = addon.get("id")

        total_seats = 1 # Default base
        active_addons = []

        for item in items:
            price_id = item.get("price", {}).get("id")
            quantity = item.get("quantity", 1)
            
            if price_id == seat_price_id:
                # Assuming additional seats are purely additive to the base 1
                total_seats = 1 + quantity
            elif price_id in addon_price_map:
                addon_id = addon_price_map[price_id]
                if addon_id not in active_addons:
                    active_addons.append(addon_id)
        
        business.seat_limit = total_seats
        business.active_addons = active_addons
        
        await self.session.commit()
        self.logger.info(f"Updated subscription for business {business.id}: status={status}, seats={total_seats}, addons={active_addons}")

    async def _handle_subscription_deleted(self, subscription: dict):
        await self._handle_subscription_updated(subscription)
