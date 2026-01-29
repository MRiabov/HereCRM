import asyncio
from typing import Optional

import os
import yaml
import stripe
import logging
import httpx
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
            self.logger.warning(
                "STRIPE_SECRET_KEY not set. Billing operations will fail."
            )
        stripe.api_key = stripe_key

        # Load billing config
        self.config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "billing_config.yaml"
        )
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

        # Calculate messaging stats
        msg_usage_config = self.config.get("products", {}).get("messaging", {})
        free_tier = msg_usage_config.get("free_limit", 1000)
        overage_rate = msg_usage_config.get("overage_rate", 0.02)

        msg_count = business.message_count_current_period
        credits = business.message_credits

        # Overage is simply negative credits
        overage = max(0, -credits)
        overage_cost = overage * overage_rate

        return {
            "status": business.subscription_status,
            "seat_limit": business.seat_limit,
            "active_addons": business.active_addons,
            "stripe_customer_id": business.stripe_customer_id,
            "usage": {
                "messages": msg_count,
                "free_limit": free_tier,  # Static 1000/mo info
                "credits": credits,
                "overage": overage,
                "estimated_cost": overage_cost,
            },
        }

    async def track_message_sent(self, business_id: int, quantity: int = 1):
        """Decrements usage counter and reports to Stripe."""
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            return

        # New Logic: Simple Counter
        old_credits = business.message_credits
        business.message_credits -= quantity
        business.message_count_current_period += quantity  # Keep stats tracking

        # Calculate billable usage
        # We only report usage that exceeds the available positive credits
        # If I had 2 credits and used 5, I pay for 3.
        # If I had -2 credits and used 5, I pay for 5.
        billable_quantity = max(0, quantity - max(0, old_credits))

        # Report usage to Stripe if active subscription exists and we have billable usage
        if billable_quantity > 0 and business.stripe_subscription_id:
            try:
                price_id = (
                    self.config.get("products", {}).get("messaging", {}).get("price_id")
                )
                if price_id:
                    si_id = await self._get_subscription_item_by_price(
                        business.stripe_subscription_id, price_id
                    )
                    if si_id:
                        await self._report_usage_raw(si_id, billable_quantity)
            except Exception as e:
                self.logger.error(f"Stripe usage report failed: {e}")

        await self.session.commit()

    async def _get_subscription_item_by_price(
        self, subscription_id: str, price_id: str
    ) -> Optional[str]:
        try:
            subscription = await asyncio.to_thread(
                stripe.Subscription.retrieve, subscription_id
            )
            for item in subscription.get("items", {}).get("data", []):
                if item.get("price", {}).get("id") == price_id:
                    return item.get("id")
        except Exception as e:
            self.logger.error(f"Failed to retrieve subscription items: {e}")
        return None

    async def _report_usage_raw(self, subscription_item_id: str, quantity: int):
        """Reports usage to Stripe using raw HTTP request due to SDK limitations."""
        url = f"https://api.stripe.com/v1/subscription_items/{subscription_item_id}/usage_records"
        headers = {
            "Authorization": f"Bearer {stripe.api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"quantity": str(quantity), "action": "increment", "timestamp": "now"}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()

    async def create_checkout_session(
        self,
        business_id: int,
        price_id: str,
        success_url: str,
        cancel_url: str,
        mode: str = "subscription",
    ) -> str:
        """Creates a new checkout session (subscription or payment)."""
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
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {"business_id": str(business_id)},
        }

        # If we have a customer ID, attach it
        if business.stripe_customer_id:
            params["customer"] = business.stripe_customer_id

        try:
            session = await asyncio.to_thread(stripe.checkout.Session.create, **params)
            return session.url
        except stripe.error.StripeError as e:
            self.logger.error(
                f"Stripe session creation failed for business {business_id}: {e}"
            )
            raise

    async def create_upgrade_link(
        self,
        business_id: int,
        item_type: str,
        item_id: Optional[str],
        success_url: str,
        cancel_url: str,
    ) -> dict:
        """Creates an upgrade link with proration if possible."""
        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            raise ValueError("Business not found")

        # Find the price_id from config
        price_id = None
        item_name = item_id or item_type

        if item_type == "seat":
            seat_config = self.config.get("products", {}).get("seat", {})
            price_id = seat_config.get("price_id")
            item_name = seat_config.get("name", "Additional Seat")
        elif item_type == "messaging":
            msg_config = self.config.get("products", {}).get("messaging", {})
            price_id = msg_config.get("price_id")
            item_name = msg_config.get("name", "Messaging Package")
        elif item_type == "addon":
            for addon in self.config.get("addons", []):
                if addon.get("id") == item_id:
                    price_id = addon.get("price_id")
                    item_name = addon.get("name", item_id)
                    break

        if not price_id:
            raise ValueError(f"Invalid item: {item_type}/{item_id}")

        self.logger.info(
            f"Creating upgrade link for business {business_id}, item {item_name}"
        )

        mode = "subscription"
        if item_type == "messaging":
            mode = "payment"

        try:
            url = await self.create_checkout_session(
                business_id, price_id, success_url, cancel_url, mode=mode
            )
            return {"url": url, "description": f"Upgrade: {item_name}"}
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
        elif event_type == "invoice.created":
            await self._handle_invoice_created(data)

    async def _handle_invoice_created(self, invoice: dict):
        customer_id = invoice.get("customer")
        if not customer_id:
            return

        result = await self.session.execute(
            select(Business).where(Business.stripe_customer_id == customer_id)
        )
        business = result.scalar_one_or_none()

        if business:
            self.logger.info(
                f"Resetting message usage Stats and adding monthly credits for business {business.id}"
            )
            business.message_count_current_period = 0  # Reset stats
            business.message_credits += 1000  # Add monthly allowance (Carry over)

            from datetime import datetime, timezone

            business.billing_cycle_anchor = datetime.now(timezone.utc)
            await self.session.commit()

    async def _handle_checkout_completed(self, session: dict):
        metadata = session.get("metadata", {})
        business_id = metadata.get("business_id")

        if not business_id:
            self.logger.warning(
                f"Webhook {session.get('id')} missing business_id metadata"
            )
            return

        business_id = int(business_id)
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        business = await self.business_repo.get_by_id_global(business_id)
        if not business:
            self.logger.error(
                f"Business {business_id} not found for webhook {session.get('id')}"
            )
            return

        business.stripe_customer_id = customer_id

        # If subscription, store it and activate
        if subscription_id:
            business.stripe_subscription_id = subscription_id
            business.subscription_status = "active"

        # Handle one-time payment for messaging credits
        mode = session.get("mode")
        if mode == "payment":
            # Check if this was a messaging top-up
            # We need to verify what was bought by expanding the session or checking line items
            # But effectively we can check if the price ID matches our messaging config
            # Or simpler: Is this a "payment" mode session for this business?
            # We should probably fetch line items to be sure, but for MVP let's assume if it's payment it's credits
            # or check the amount/price from session (requires fetching session line items)

            # Fetch line items to confirm product
            try:
                line_items = await asyncio.to_thread(
                    stripe.checkout.Session.list_line_items, session.get("id"), limit=5
                )
                msg_price_id = (
                    self.config.get("products", {}).get("messaging", {}).get("price_id")
                )

                is_messaging = False
                for item in line_items.get("data", []):
                    if item.get("price", {}).get("id") == msg_price_id:
                        is_messaging = True
                        break

                if is_messaging:
                    # Grant 1000 credits
                    # We use default 1000, or should we use quantity * 1000?
                    # Assuming quantity=1 means 1 pack = 1000 credits.
                    credits_to_add = 1000
                    business.message_credits += credits_to_add
                    self.logger.info(
                        f"Added {credits_to_add} message credits to business {business.id}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to process line items for session {session.get('id')}: {e}"
                )

        await self.session.commit()
        self.logger.info(
            f"processed checkout for business {business_id} (customer {customer_id})"
        )

    async def _handle_subscription_updated(self, subscription: dict):
        customer_id = subscription.get("customer")
        metadata = subscription.get("metadata", {})
        business_id = metadata.get("business_id")

        business = None
        if business_id:
            business = await self.business_repo.get_by_id_global(int(business_id))

        if not business and customer_id:
            # Find by customer_id
            result = await self.session.execute(
                select(Business).where(Business.stripe_customer_id == customer_id)
            )
            business = result.scalar_one_or_none()

        if not business:
            self.logger.error(
                f"Business not found for subscription {subscription.get('id')}"
            )
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

        total_seats = 1  # Default base
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
        self.logger.info(
            f"Updated subscription for business {business.id}: status={status}, seats={total_seats}, addons={active_addons}"
        )

    async def _handle_subscription_deleted(self, subscription: dict):
        await self._handle_subscription_updated(subscription)
