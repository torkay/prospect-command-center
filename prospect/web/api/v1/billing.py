"""Stripe billing API endpoints."""

import logging
import os
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from prospect.web.database import get_db, User
from prospect.web.auth import get_current_user
from prospect.web.api.v1.usage import update_user_tier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# Stripe configuration
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")

# Price IDs for each tier (configure these in Stripe Dashboard)
TIER_PRICES = {
    "scout": "price_scout_monthly",      # $99/month
    "hunter": "price_hunter_monthly",    # $149/month (beta) or $249/month
    "command": "price_command_monthly",  # $499/month
}

# Reverse mapping from price ID to tier
PRICE_TO_TIER = {v: k for k, v in TIER_PRICES.items()}


class CreateCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe checkout session."""
    tier: str
    success_url: str
    cancel_url: str


class CreateCheckoutSessionResponse(BaseModel):
    """Response with checkout session URL."""
    session_url: str
    session_id: str


class PortalSessionResponse(BaseModel):
    """Response with billing portal URL."""
    portal_url: str


class SubscriptionStatusResponse(BaseModel):
    """Current subscription status for the user."""
    tier: str
    subscription_status: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_end: Optional[str] = None


def get_or_create_stripe_customer(db: Session, user: User) -> str:
    """Get existing Stripe customer or create a new one."""
    if user.stripe_customer_id:
        return user.stripe_customer_id

    # Create new Stripe customer
    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={
            "user_id": str(user.id),
        }
    )

    # Save customer ID to user
    user.stripe_customer_id = customer.id
    db.commit()
    db.refresh(user)

    return customer.id


@router.post("/create-checkout-session", response_model=CreateCheckoutSessionResponse)
def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe checkout session for subscription purchase.

    Redirects user to Stripe-hosted checkout page.
    """
    # Validate tier
    if request.tier not in TIER_PRICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier. Must be one of: {', '.join(TIER_PRICES.keys())}",
        )

    # Get or create Stripe customer
    customer_id = get_or_create_stripe_customer(db, current_user)

    try:
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[
                {
                    "price": TIER_PRICES[request.tier],
                    "quantity": 1,
                }
            ],
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "tier": request.tier,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(current_user.id),
                    "tier": request.tier,
                }
            },
        )

        return CreateCheckoutSessionResponse(
            session_url=checkout_session.url,
            session_id=checkout_session.id,
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session. Please try again.",
        )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Stripe webhooks.

    This endpoint receives events from Stripe and updates user subscription status.
    No authentication required - verified via webhook signature.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"Received Stripe webhook: {event_type}")

    if event_type == "checkout.session.completed":
        await handle_checkout_completed(db, data)

    elif event_type == "invoice.paid":
        await handle_invoice_paid(db, data)

    elif event_type == "invoice.payment_failed":
        await handle_payment_failed(db, data)

    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(db, data)

    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(db, data)

    return {"status": "success"}


async def handle_checkout_completed(db: Session, session: dict):
    """Handle successful checkout completion."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})

    user_id = metadata.get("user_id")
    tier = metadata.get("tier")

    if not user_id:
        # Try to find user by customer ID
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    else:
        user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        logger.error(f"User not found for checkout session. customer_id={customer_id}, user_id={user_id}")
        return

    # Update user with subscription info
    user.stripe_subscription_id = subscription_id
    user.subscription_status = "active"

    # Update tier and limits
    if tier:
        update_user_tier(db, user, tier)
    else:
        db.commit()

    logger.info(f"Checkout completed for user {user.id}, tier={tier}, subscription={subscription_id}")


async def handle_invoice_paid(db: Session, invoice: dict):
    """Handle successful invoice payment (subscription renewal)."""
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        logger.error(f"User not found for paid invoice. customer_id={customer_id}")
        return

    # Ensure subscription is marked as active
    user.subscription_status = "active"
    user.stripe_subscription_id = subscription_id
    db.commit()

    logger.info(f"Invoice paid for user {user.id}")


async def handle_payment_failed(db: Session, invoice: dict):
    """Handle failed invoice payment."""
    customer_id = invoice.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        logger.error(f"User not found for failed payment. customer_id={customer_id}")
        return

    # Mark subscription as past due
    user.subscription_status = "past_due"
    db.commit()

    logger.warning(f"Payment failed for user {user.id}")


async def handle_subscription_deleted(db: Session, subscription: dict):
    """Handle subscription cancellation/deletion."""
    customer_id = subscription.get("customer")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        logger.error(f"User not found for deleted subscription. customer_id={customer_id}")
        return

    # Mark subscription as canceled and downgrade to scout tier
    user.subscription_status = "canceled"
    user.stripe_subscription_id = None
    update_user_tier(db, user, "scout")

    logger.info(f"Subscription canceled for user {user.id}, downgraded to scout")


async def handle_subscription_updated(db: Session, subscription: dict):
    """Handle subscription updates (plan changes, etc.)."""
    customer_id = subscription.get("customer")
    subscription_status = subscription.get("status")

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

    if not user:
        logger.error(f"User not found for subscription update. customer_id={customer_id}")
        return

    # Update subscription status
    if subscription_status in ("active", "trialing"):
        user.subscription_status = "active"
    elif subscription_status == "past_due":
        user.subscription_status = "past_due"
    elif subscription_status in ("canceled", "unpaid"):
        user.subscription_status = "canceled"

    # Check if tier changed (plan change)
    items = subscription.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id")
        if price_id and price_id in PRICE_TO_TIER:
            new_tier = PRICE_TO_TIER[price_id]
            update_user_tier(db, user, new_tier)
            logger.info(f"User {user.id} plan changed to {new_tier}")
            return

    db.commit()
    logger.info(f"Subscription updated for user {user.id}, status={subscription_status}")


@router.post("/portal", response_model=PortalSessionResponse)
def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe billing portal session.

    Allows users to manage their subscription, update payment methods, view invoices.
    """
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    try:
        # Get the return URL from environment or use a default
        return_url = os.environ.get("APP_URL", "http://localhost:3000") + "/settings/billing"

        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=return_url,
        )

        return PortalSessionResponse(portal_url=portal_session.url)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create billing portal session. Please try again.",
        )


@router.get("/status", response_model=SubscriptionStatusResponse)
def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current subscription status for the authenticated user.
    """
    current_period_end = None

    # If user has an active subscription, get additional details from Stripe
    if current_user.stripe_subscription_id and current_user.subscription_status == "active":
        try:
            subscription = stripe.Subscription.retrieve(current_user.stripe_subscription_id)
            if subscription.current_period_end:
                from datetime import datetime
                current_period_end = datetime.fromtimestamp(
                    subscription.current_period_end
                ).isoformat()
        except stripe.error.StripeError as e:
            logger.warning(f"Could not fetch subscription details: {e}")

    return SubscriptionStatusResponse(
        tier=current_user.tier,
        subscription_status=current_user.subscription_status,
        stripe_customer_id=current_user.stripe_customer_id,
        stripe_subscription_id=current_user.stripe_subscription_id,
        current_period_end=current_period_end,
    )
