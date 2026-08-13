from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User
from app.models.subscription_models import (
    Plan, PlanLimit, Subscription, Transaction, AiFeatureSetting, CreditPackage, PaymentMethodConfig,
)
from app.security import require_admin
from app.services.pagination import paginate, page_response
from app.services.subscription_limits import FEATURE_KEYS
from app.services.stripe_client import sync_plan_to_stripe
from app.services.subscription_admin import (
    get_or_seed_feature_settings,
    get_or_seed_payment_methods,
    compute_subscription_analytics,
)

router = APIRouter(prefix="/admin/subscriptions", tags=["Admin - Subscriptions"])


def _serialize_plan(plan: Plan) -> dict:
    return {
        "id": plan.id,
        "name": plan.name,
        "slug": plan.slug,
        "description": plan.description,
        "monthlyPriceCents": plan.monthly_price_cents,
        "yearlyPriceCents": plan.yearly_price_cents,
        "monthlyCredits": plan.monthly_credits,
        "currency": plan.currency,
        "isActive": plan.is_active,
        "displayOrder": plan.display_order,
        "stripeProductId": plan.stripe_product_id,
        "createdAt": plan.created_at,
        "updatedAt": plan.updated_at,
    }


def _serialize_limit(limit: PlanLimit) -> dict:
    return {"featureKey": limit.feature_key, "dailyLimit": limit.daily_limit, "monthlyLimit": limit.monthly_limit}


@router.get("/plans")
def list_plans(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(Plan)
    if search:
        query = query.filter(Plan.name.ilike(f"%{search}%"))
    if status == "active":
        query = query.filter(Plan.is_active.is_(True))
    elif status == "inactive":
        query = query.filter(Plan.is_active.is_(False))

    query = query.order_by(Plan.display_order, Plan.id)
    items, total = paginate(query, page, pageSize)
    return page_response([_serialize_plan(plan) for plan in items], total, page, pageSize)


class PlanCreateInput(BaseModel):
    name: str
    slug: str
    description: str | None = None
    monthlyPriceCents: int
    yearlyPriceCents: int | None = None
    monthlyCredits: int = 0
    currency: str = "usd"
    displayOrder: int = 0


@router.post("/plans")
def create_plan(data: PlanCreateInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    existing = db.query(Plan).filter(Plan.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="A plan with that slug already exists.")
    if data.monthlyCredits < 0:
        raise HTTPException(status_code=400, detail="Included tokens can't be negative.")

    plan = Plan(
        name=data.name,
        slug=data.slug,
        description=data.description,
        monthly_price_cents=data.monthlyPriceCents,
        yearly_price_cents=data.yearlyPriceCents,
        monthly_credits=data.monthlyCredits,
        currency=data.currency,
        display_order=data.displayOrder,
    )
    try:
        sync_plan_to_stripe(plan)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not sync plan to Stripe: {str(e)}")

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


class PlanUpdateInput(BaseModel):
    name: str | None = None
    description: str | None = None
    monthlyPriceCents: int | None = None
    yearlyPriceCents: int | None = None
    monthlyCredits: int | None = None
    currency: str | None = None
    displayOrder: int | None = None


@router.patch("/plans/{plan_id}")
def update_plan(
    plan_id: int, data: PlanUpdateInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    price_changed = (
        (data.monthlyPriceCents is not None and data.monthlyPriceCents != plan.monthly_price_cents)
        or (data.yearlyPriceCents is not None and data.yearlyPriceCents != plan.yearly_price_cents)
    )

    if data.name is not None:
        plan.name = data.name
    if data.description is not None:
        plan.description = data.description
    if data.monthlyPriceCents is not None:
        plan.monthly_price_cents = data.monthlyPriceCents
    if data.yearlyPriceCents is not None:
        plan.yearly_price_cents = data.yearlyPriceCents
    if data.monthlyCredits is not None:
        if data.monthlyCredits < 0:
            raise HTTPException(status_code=400, detail="Included tokens can't be negative.")
        plan.monthly_credits = data.monthlyCredits
    if data.currency is not None:
        plan.currency = data.currency
    if data.displayOrder is not None:
        plan.display_order = data.displayOrder

    if price_changed or data.name is not None or data.description is not None:
        try:
            sync_plan_to_stripe(plan)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=502, detail=f"Could not sync plan to Stripe: {str(e)}")

    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


class PlanStatusInput(BaseModel):
    isActive: bool


@router.patch("/plans/{plan_id}/status")
def set_plan_status(
    plan_id: int, data: PlanStatusInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_active = data.isActive
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


@router.delete("/plans/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    subscriber_count = db.query(Subscription).filter(Subscription.plan_id == plan_id).count()
    if subscriber_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Can't delete a plan with {subscriber_count} subscriber(s) — deactivate it instead.",
        )

    db.query(PlanLimit).filter(PlanLimit.plan_id == plan_id).delete()
    db.delete(plan)
    db.commit()
    return {"message": "Plan deleted."}


@router.get("/plans/{plan_id}/limits")
def get_plan_limits(plan_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    existing = {limit.feature_key: limit for limit in db.query(PlanLimit).filter(PlanLimit.plan_id == plan_id).all()}
    return [
        _serialize_limit(existing[key]) if key in existing else {"featureKey": key, "dailyLimit": None, "monthlyLimit": None}
        for key in FEATURE_KEYS
    ]


class PlanLimitInput(BaseModel):
    featureKey: str
    dailyLimit: int | None = None
    monthlyLimit: int | None = None


class PlanLimitsUpdateInput(BaseModel):
    limits: list[PlanLimitInput]


@router.put("/plans/{plan_id}/limits")
def update_plan_limits(
    plan_id: int, data: PlanLimitsUpdateInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    invalid_keys = [entry.featureKey for entry in data.limits if entry.featureKey not in FEATURE_KEYS]
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Unknown feature key(s): {', '.join(invalid_keys)}")

    existing = {limit.feature_key: limit for limit in db.query(PlanLimit).filter(PlanLimit.plan_id == plan_id).all()}
    for entry in data.limits:
        if entry.featureKey in existing:
            existing[entry.featureKey].daily_limit = entry.dailyLimit
            existing[entry.featureKey].monthly_limit = entry.monthlyLimit
        else:
            db.add(PlanLimit(plan_id=plan_id, feature_key=entry.featureKey, daily_limit=entry.dailyLimit, monthly_limit=entry.monthlyLimit))

    db.commit()
    return get_plan_limits(plan_id, db, current_user)


# ---------------------------------------------------------------------------
# AI feature settings — global, cross-plan controls: does a feature require
# payment at all once a plan's included allowance runs out, and at what
# credit cost. See app/services/feature_gate.py for how these get enforced.
# ---------------------------------------------------------------------------

def _serialize_feature_setting(setting: AiFeatureSetting) -> dict:
    return {
        "featureKey": setting.feature_key,
        "featureLabel": setting.feature_label,
        "isPaid": setting.is_paid,
        "creditCostPerUse": setting.credit_cost_per_use,
        "isEnabled": setting.is_enabled,
    }


@router.get("/feature-settings")
def list_feature_settings(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return [_serialize_feature_setting(setting) for setting in get_or_seed_feature_settings(db)]


class FeatureSettingUpdateInput(BaseModel):
    isPaid: bool
    creditCostPerUse: int = 0
    isEnabled: bool = True


@router.put("/feature-settings/{feature_key}")
def update_feature_setting(
    feature_key: str, data: FeatureSettingUpdateInput,
    db: Session = Depends(get_db), current_user: User = Depends(require_admin),
):
    if feature_key not in FEATURE_KEYS:
        raise HTTPException(status_code=400, detail=f"Unknown feature key: {feature_key}")
    if data.creditCostPerUse < 0:
        raise HTTPException(status_code=400, detail="Credit cost can't be negative.")

    get_or_seed_feature_settings(db)  # ensures a row exists for every known feature
    setting = db.query(AiFeatureSetting).filter(AiFeatureSetting.feature_key == feature_key).first()
    setting.is_paid = data.isPaid
    setting.credit_cost_per_use = data.creditCostPerUse
    setting.is_enabled = data.isEnabled
    db.commit()
    db.refresh(setting)
    return _serialize_feature_setting(setting)


# ---------------------------------------------------------------------------
# Credit packages
# ---------------------------------------------------------------------------

def _serialize_package(package: CreditPackage) -> dict:
    return {
        "id": package.id,
        "name": package.name,
        "credits": package.credits,
        "priceCents": package.price_cents,
        "currency": package.currency,
        "isActive": package.is_active,
        "displayOrder": package.display_order,
        "createdAt": package.created_at,
    }


@router.get("/credit-packages")
def list_credit_packages(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    packages = db.query(CreditPackage).order_by(CreditPackage.display_order, CreditPackage.id).all()
    return [_serialize_package(p) for p in packages]


class CreditPackageInput(BaseModel):
    name: str
    credits: int
    priceCents: int
    currency: str = "usd"
    displayOrder: int = 0


@router.post("/credit-packages")
def create_credit_package(data: CreditPackageInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    if data.credits <= 0 or data.priceCents <= 0:
        raise HTTPException(status_code=400, detail="Credits and price must both be positive.")
    package = CreditPackage(
        name=data.name, credits=data.credits, price_cents=data.priceCents,
        currency=data.currency, display_order=data.displayOrder,
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return _serialize_package(package)


@router.patch("/credit-packages/{package_id}")
def update_credit_package(
    package_id: int, data: CreditPackageInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    package = db.query(CreditPackage).filter(CreditPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Credit package not found")
    if data.credits <= 0 or data.priceCents <= 0:
        raise HTTPException(status_code=400, detail="Credits and price must both be positive.")

    package.name = data.name
    package.credits = data.credits
    package.price_cents = data.priceCents
    package.currency = data.currency
    package.display_order = data.displayOrder
    db.commit()
    db.refresh(package)
    return _serialize_package(package)


class PackageStatusInput(BaseModel):
    isActive: bool


@router.patch("/credit-packages/{package_id}/status")
def set_credit_package_status(
    package_id: int, data: PackageStatusInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    package = db.query(CreditPackage).filter(CreditPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Credit package not found")
    package.is_active = data.isActive
    db.commit()
    db.refresh(package)
    return _serialize_package(package)


@router.delete("/credit-packages/{package_id}")
def delete_credit_package(package_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    package = db.query(CreditPackage).filter(CreditPackage.id == package_id).first()
    if not package:
        raise HTTPException(status_code=404, detail="Credit package not found")
    db.delete(package)
    db.commit()
    return {"message": "Credit package deleted."}


# ---------------------------------------------------------------------------
# Payment methods
# ---------------------------------------------------------------------------

def _serialize_payment_method(method: PaymentMethodConfig) -> dict:
    return {"methodKey": method.method_key, "label": method.label, "isEnabled": method.is_enabled}


@router.get("/payment-methods")
def list_payment_methods(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return [_serialize_payment_method(m) for m in get_or_seed_payment_methods(db)]


class PaymentMethodStatusInput(BaseModel):
    isEnabled: bool


@router.patch("/payment-methods/{method_key}/status")
def set_payment_method_status(
    method_key: str, data: PaymentMethodStatusInput, db: Session = Depends(get_db), current_user: User = Depends(require_admin)
):
    get_or_seed_payment_methods(db)
    method = db.query(PaymentMethodConfig).filter(PaymentMethodConfig.method_key == method_key).first()
    if not method:
        raise HTTPException(status_code=404, detail="Unknown payment method")
    method.is_enabled = data.isEnabled
    db.commit()
    db.refresh(method)
    return _serialize_payment_method(method)


# ---------------------------------------------------------------------------
# Subscribers & transactions
# ---------------------------------------------------------------------------

@router.get("/subscribers")
def list_subscribers(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    planId: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(Subscription, User, Plan).join(User, User.id == Subscription.user_id).join(Plan, Plan.id == Subscription.plan_id)
    if planId is not None:
        query = query.filter(Subscription.plan_id == planId)
    if status:
        query = query.filter(Subscription.status == status)
    query = query.order_by(Subscription.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * pageSize).limit(pageSize).all()
    items = [
        {
            "subscriptionId": sub.id,
            "userId": user.id,
            "userName": user.full_name or user.email,
            "userEmail": user.email,
            "planId": plan.id,
            "planName": plan.name,
            "status": sub.status,
            "billingCycle": sub.billing_cycle,
            "currentPeriodEnd": sub.current_period_end,
            "cancelAtPeriodEnd": sub.cancel_at_period_end,
        }
        for sub, user, plan in rows
    ]
    return page_response(items, total, page, pageSize)


@router.get("/transactions")
def list_transactions(
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: str | None = None,
    kind: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    query = db.query(Transaction, User).join(User, User.id == Transaction.user_id)
    if status:
        query = query.filter(Transaction.status == status)
    if kind:
        query = query.filter(Transaction.kind == kind)
    query = query.order_by(Transaction.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * pageSize).limit(pageSize).all()
    items = [
        {
            "id": tx.id,
            "userId": user.id,
            "userName": user.full_name or user.email,
            "kind": tx.kind,
            "amountCents": tx.amount_cents,
            "currency": tx.currency,
            "status": tx.status,
            "paymentMethod": tx.payment_method,
            "creditsPurchased": tx.credits_purchased,
            "externalReference": tx.external_reference,
            "createdAt": tx.created_at,
        }
        for tx, user in rows
    ]
    return page_response(items, total, page, pageSize)


@router.get("/analytics")
def get_subscription_analytics(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return compute_subscription_analytics(db)
