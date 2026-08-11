"""Stripe integration for plan sync, checkout, and billing portal.

Gated by STRIPE_SECRET_KEY the same way email/AI features are gated elsewhere
in this app (see email_service.is_email_configured()): if it isn't set,
is_stripe_configured() is False and admin plan CRUD still works locally
(prices/limits are editable) but nothing is synced to Stripe, so there's no
hard dependency on having a Stripe account just to manage plan data.

    STRIPE_SECRET_KEY     - test or live secret key (sk_test_... / sk_live_...)
    STRIPE_WEBHOOK_SECRET - signing secret for the /webhooks/stripe endpoint,
                             from `stripe listen` (dev) or the Stripe Dashboard
                             webhook config (prod)
"""
import os
import logging

import stripe

from app.models.subscription_models import Plan

logger = logging.getLogger(__name__)


def is_stripe_configured() -> bool:
    return bool(os.getenv("STRIPE_SECRET_KEY"))


def _client() -> None:
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def sync_plan_to_stripe(plan: Plan) -> None:
    """Creates/updates the Stripe Product for this plan, and (re)creates its
    Price objects. Stripe Prices are immutable once created — you can't edit
    an amount in place — so this always creates a fresh Price and archives
    whichever one it's replacing. Mutates plan.stripe_* fields in place;
    caller is responsible for committing. No-ops silently if Stripe isn't
    configured, so plan CRUD keeps working without a Stripe account."""
    if not is_stripe_configured():
        return
    _client()

    try:
        if plan.stripe_product_id:
            stripe.Product.modify(plan.stripe_product_id, name=plan.name, description=plan.description or "")
        else:
            product = stripe.Product.create(name=plan.name, description=plan.description or "")
            plan.stripe_product_id = product.id

        old_monthly_price_id = plan.stripe_monthly_price_id
        monthly_price = stripe.Price.create(
            product=plan.stripe_product_id,
            unit_amount=plan.monthly_price_cents,
            currency=plan.currency,
            recurring={"interval": "month"},
        )
        plan.stripe_monthly_price_id = monthly_price.id
        if old_monthly_price_id:
            stripe.Price.modify(old_monthly_price_id, active=False)

        old_yearly_price_id = plan.stripe_yearly_price_id
        if plan.yearly_price_cents is not None:
            yearly_price = stripe.Price.create(
                product=plan.stripe_product_id,
                unit_amount=plan.yearly_price_cents,
                currency=plan.currency,
                recurring={"interval": "year"},
            )
            plan.stripe_yearly_price_id = yearly_price.id
        else:
            plan.stripe_yearly_price_id = None
        if old_yearly_price_id and old_yearly_price_id != plan.stripe_yearly_price_id:
            stripe.Price.modify(old_yearly_price_id, active=False)
    except stripe.error.StripeError:
        logger.warning("stripe_client.sync_plan_to_stripe failed for plan_id=%s", plan.id, exc_info=True)
        raise


def get_or_create_stripe_customer(user) -> str | None:
    """Returns the Stripe Customer ID for this user, creating one if needed.
    Caller passes in the user's existing Subscription.stripe_customer_id (if
    any) via the `existing_customer_id` check happening at the call site —
    this function only creates when told there isn't one yet."""
    if not is_stripe_configured():
        return None
    _client()
    customer = stripe.Customer.create(email=user.email, name=user.full_name or None, metadata={"user_id": str(user.id)})
    return customer.id


def create_checkout_session(customer_id: str, price_id: str, success_url: str, cancel_url: str) -> str:
    """Creates a Stripe Checkout Session in subscription mode for the given
    Price ID and returns the hosted checkout URL to redirect the browser to."""
    _client()
    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """Creates a Stripe Billing Portal session so the user can update their
    card, view invoices, or cancel — all via Stripe's hosted UI."""
    _client()
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    return session.url


def construct_webhook_event(payload: bytes, sig_header: str):
    _client()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    return stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
