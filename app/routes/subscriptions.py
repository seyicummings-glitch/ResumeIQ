"""User-facing subscription/credit endpoints — the counterpart to
app/routes/admin_subscriptions.py's admin controls. Every AI feature's
actual usage gating happens in app/services/feature_gate.py at each
feature's own route (resume_builder.py, matching.py, interview.py, ...);
this file is what a user reads/acts on directly: their plan, credit
balance, usage-so-far, and the purchase flows.

Payments here go through app/services/payment_gateway.py, which is
currently a TEST-MODE simulation (see that module's docstring) — no real
money moves and no card data is ever accepted by any endpoint below.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.models.subscription_models import Plan, Subscription, Transaction, CreditPackage, CreditLedgerEntry
from app.security import get_current_user
from app.services.pagination import paginate, page_response
from app.services.subscription_limits import FEATURE_KEYS
from app.services.subscription_admin import get_or_seed_payment_methods
from app.services.payment_gateway import process_payment
from app.services.feature_gate import (
    get_or_create_subscription, get_feature_usage_summary, adjust_credits, get_credit_balance, next_free_refresh_at,
)
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("/me")
def get_my_subscription(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = get_or_create_subscription(db, current_user)
    plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first() if subscription else None

    return {
        "plan": {
            "id": plan.id, "name": plan.name, "slug": plan.slug,
            "monthlyPriceCents": plan.monthly_price_cents, "yearlyPriceCents": plan.yearly_price_cents,
            "monthlyCredits": plan.monthly_credits,
        } if plan else None,
        "status": subscription.status if subscription else None,
        "billingCycle": subscription.billing_cycle if subscription else None,
        "currentPeriodEnd": subscription.current_period_end if subscription else None,
        "creditBalance": get_credit_balance(db, current_user.id),
        "nextFreeRefreshAt": next_free_refresh_at(db, current_user, subscription) if subscription else None,
        "usage": [get_feature_usage_summary(db, current_user, key) for key in FEATURE_KEYS],
    }


@router.get("/plans")
def list_public_plans(db: Session = Depends(get_db)):
    """No auth required — used for the "compare plans" / upgrade picker,
    which a logged-out visitor can reasonably browse too."""
    plans = db.query(Plan).filter(Plan.is_active.is_(True)).order_by(Plan.display_order, Plan.id).all()
    return [
        {
            "id": plan.id, "name": plan.name, "slug": plan.slug, "description": plan.description,
            "monthlyPriceCents": plan.monthly_price_cents, "yearlyPriceCents": plan.yearly_price_cents,
            "monthlyCredits": plan.monthly_credits, "currency": plan.currency,
        }
        for plan in plans
    ]


@router.get("/payment-methods")
def list_available_payment_methods(db: Session = Depends(get_db)):
    """No auth required, same reasoning as /plans -- and only enabled
    methods are ever returned, so an admin-disabled method never shows up
    in a checkout UI even briefly."""
    methods = get_or_seed_payment_methods(db)
    return [{"methodKey": m.method_key, "label": m.label} for m in methods if m.is_enabled]


class UpgradeInput(BaseModel):
    planId: int
    billingCycle: str = "monthly"  # "monthly" | "yearly"
    paymentMethod: str


@router.post("/upgrade")
def upgrade_plan(
    data: UpgradeInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    plan = db.query(Plan).filter(Plan.id == data.planId, Plan.is_active.is_(True)).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or not currently available.")
    if data.billingCycle not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="billingCycle must be 'monthly' or 'yearly'.")

    amount_cents = plan.yearly_price_cents if data.billingCycle == "yearly" else plan.monthly_price_cents
    if amount_cents is None:
        raise HTTPException(status_code=400, detail=f"This plan has no {data.billingCycle} price configured.")

    # A free plan ($0) never needs to go through the payment gateway at all.
    if amount_cents > 0:
        result = process_payment(data.paymentMethod, amount_cents, plan.currency)
        if result.status != "succeeded":
            db.add(Transaction(
                user_id=current_user.id, plan_id=plan.id, kind="subscription", amount_cents=amount_cents,
                currency=plan.currency, status="failed", payment_method=data.paymentMethod,
            ))
            db.commit()
            raise HTTPException(status_code=402, detail=result.message)

    now = datetime.now(timezone.utc)
    period_length = timedelta(days=365) if data.billingCycle == "yearly" else timedelta(days=30)

    subscription = get_or_create_subscription(db, current_user)
    subscription.plan_id = plan.id
    subscription.billing_cycle = data.billingCycle
    subscription.status = "active"
    subscription.current_period_start = now
    subscription.current_period_end = now + period_length
    subscription.cancel_at_period_end = False

    if amount_cents > 0:
        db.add(Transaction(
            user_id=current_user.id, plan_id=plan.id, kind="subscription", amount_cents=amount_cents,
            currency=plan.currency, status="paid", payment_method=data.paymentMethod,
            external_reference=result.external_reference,
        ))

    db.commit()

    new_balance = get_credit_balance(db, current_user.id)
    if plan.monthly_credits > 0:
        new_balance = adjust_credits(
            db, current_user.id, plan.monthly_credits, reason="subscription_grant",
            reference_id=subscription.id,
        )

    return {
        "message": f"You're now on the {plan.name} plan.",
        "planId": plan.id,
        "billingCycle": data.billingCycle,
        "creditsGranted": plan.monthly_credits,
        "creditBalance": new_balance,
    }


@router.get("/credit-packages")
def list_available_credit_packages(db: Session = Depends(get_db)):
    packages = (
        db.query(CreditPackage)
        .filter(CreditPackage.is_active.is_(True))
        .order_by(CreditPackage.display_order, CreditPackage.id)
        .all()
    )
    return [
        {"id": p.id, "name": p.name, "credits": p.credits, "priceCents": p.price_cents, "currency": p.currency}
        for p in packages
    ]


class CreditPurchaseInput(BaseModel):
    packageId: int
    paymentMethod: str


@router.post("/credits/purchase")
def purchase_credits(
    data: CreditPurchaseInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    package = db.query(CreditPackage).filter(CreditPackage.id == data.packageId, CreditPackage.is_active.is_(True)).first()
    if not package:
        raise HTTPException(status_code=404, detail="Credit package not found or no longer available.")

    result = process_payment(data.paymentMethod, package.price_cents, package.currency)
    if result.status != "succeeded":
        db.add(Transaction(
            user_id=current_user.id, kind="credit_purchase", amount_cents=package.price_cents,
            currency=package.currency, status="failed", payment_method=data.paymentMethod, credits_purchased=package.credits,
        ))
        db.commit()
        raise HTTPException(status_code=402, detail=result.message)

    transaction = Transaction(
        user_id=current_user.id, kind="credit_purchase", amount_cents=package.price_cents,
        currency=package.currency, status="paid", payment_method=data.paymentMethod,
        credits_purchased=package.credits, external_reference=result.external_reference,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    new_balance = adjust_credits(db, current_user.id, package.credits, reason="purchase", reference_id=transaction.id)

    return {
        "message": "Payment successful.",
        "amountCents": package.price_cents,
        "creditsAdded": package.credits,
        "transactionId": f"TX-{transaction.id}",
        "status": "Completed",
        "creditBalance": new_balance,
        "disclosure": "Your payment information is securely processed by our payment provider. We do not store credit card details.",
    }


@router.get("/transactions")
def get_my_transactions(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc())
    items, total = paginate(query, page, pageSize)
    return page_response([
        {
            "id": tx.id, "kind": tx.kind, "amountCents": tx.amount_cents, "currency": tx.currency,
            "status": tx.status, "paymentMethod": tx.payment_method, "creditsPurchased": tx.credits_purchased,
            "createdAt": tx.created_at,
        }
        for tx in items
    ], total, page, pageSize)


@router.get("/usage-history")
def get_my_usage_history(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(CreditLedgerEntry)
        .filter(CreditLedgerEntry.user_id == current_user.id)
        .order_by(CreditLedgerEntry.created_at.desc())
    )
    items, total = paginate(query, page, pageSize)
    return page_response([
        {
            "id": entry.id, "delta": entry.delta, "reason": entry.reason,
            "featureKey": entry.feature_key, "createdAt": entry.created_at,
        }
        for entry in items
    ], total, page, pageSize)
