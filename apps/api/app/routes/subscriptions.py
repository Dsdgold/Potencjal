"""Stripe subscription management routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.middleware.auth import get_current_user, CurrentUser
from app.models.organization import Organization, Plan, Subscription
from app.models.admin import AuditLog
from app.config import get_settings

router = APIRouter()
logger = structlog.get_logger()


@router.get("/plans")
async def list_public_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_public == True).order_by(Plan.price_monthly))
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id), "code": p.code, "name": p.name,
            "price_monthly": p.price_monthly,
            "limits": p.limits_json, "features": p.features_json,
        }
        for p in plans
    ]


@router.post("/checkout")
async def create_checkout(
    plan_code: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Płatności nie skonfigurowane")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    result = await db.execute(select(Plan).where(Plan.code == plan_code))
    plan = result.scalar_one_or_none()
    if not plan or not plan.stripe_price_id:
        raise HTTPException(status_code=404, detail="Plan nie znaleziony")

    # Get or create Stripe customer
    result = await db.execute(
        select(Subscription).where(Subscription.org_id == current_user.org_id).limit(1)
    )
    existing_sub = result.scalar_one_or_none()
    customer_id = existing_sub.provider_customer_id if existing_sub else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=current_user.email,
            metadata={"org_id": str(current_user.org_id)},
        )
        customer_id = customer.id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.NEXTAUTH_URL or 'http://localhost:3000'}/dashboard?checkout=success",
        cancel_url=f"{settings.NEXTAUTH_URL or 'http://localhost:3000'}/dashboard?checkout=cancel",
        metadata={
            "org_id": str(current_user.org_id),
            "plan_code": plan_code,
        },
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal")
async def create_portal(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Płatności nie skonfigurowane")

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    result = await db.execute(
        select(Subscription).where(Subscription.org_id == current_user.org_id).limit(1)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.provider_customer_id:
        raise HTTPException(status_code=404, detail="Brak aktywnej subskrypcji")

    session = stripe.billing_portal.Session.create(
        customer=sub.provider_customer_id,
        return_url=f"{settings.NEXTAUTH_URL or 'http://localhost:3000'}/settings",
    )

    return {"portal_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if not settings.STRIPE_SECRET_KEY:
        return {"status": "ignored"}

    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        org_id = session.get("metadata", {}).get("org_id")
        plan_code = session.get("metadata", {}).get("plan_code")

        if org_id and plan_code:
            # Update org plan
            plan_result = await db.execute(select(Plan).where(Plan.code == plan_code))
            plan = plan_result.scalar_one_or_none()
            if plan:
                org_result = await db.execute(select(Organization).where(Organization.id == org_id))
                org = org_result.scalar_one_or_none()
                if org:
                    org.plan_id = plan.id

            # Create/update subscription
            sub = Subscription(
                org_id=org_id,
                provider="stripe",
                provider_customer_id=session.get("customer"),
                provider_subscription_id=session.get("subscription"),
                status="active",
            )
            db.add(sub)

    elif event["type"] == "customer.subscription.updated":
        sub_data = event["data"]["object"]
        result = await db.execute(
            select(Subscription).where(
                Subscription.provider_subscription_id == sub_data["id"]
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = sub_data["status"]

    elif event["type"] == "customer.subscription.deleted":
        sub_data = event["data"]["object"]
        result = await db.execute(
            select(Subscription).where(
                Subscription.provider_subscription_id == sub_data["id"]
            )
        )
        sub = result.scalar_one_or_none()
        if sub:
            sub.status = "canceled"
            # Revert org to free plan
            org_result = await db.execute(select(Organization).where(Organization.id == sub.org_id))
            org = org_result.scalar_one_or_none()
            if org:
                free_plan = await db.execute(select(Plan).where(Plan.code == "free"))
                fp = free_plan.scalar_one_or_none()
                if fp:
                    org.plan_id = fp.id

    logger.info("stripe_webhook", event_type=event["type"])
    return {"status": "ok"}
