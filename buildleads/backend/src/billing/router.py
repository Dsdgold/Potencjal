"""Billing endpoints — Stripe integration stubs.

These will be fully implemented when Stripe keys are configured.
For now they return plan info and placeholder responses.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user, require_manager
from src.config import PLAN_LIMITS, settings
from src.database import get_db
from src.tenants.models import Tenant
from src.users.models import User

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


@router.get("/plan")
async def current_plan(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant = await db.get(Tenant, user.tenant_id)
    if not tenant:
        raise HTTPException(404, "Tenant not found")
    limits = PLAN_LIMITS.get(tenant.plan, {})
    return {
        "plan": tenant.plan,
        "plan_status": tenant.plan_status,
        "max_users": tenant.max_users,
        "max_regions": tenant.max_regions,
        "trial_ends_at": tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None,
        "limits": limits,
    }


@router.post("/checkout")
async def create_checkout(
    plan: str,
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(501, "Stripe not configured")
    # TODO: Create Stripe Checkout Session
    return {"message": "Stripe checkout not yet implemented", "requested_plan": plan}


@router.post("/portal")
async def customer_portal(
    user: User = Depends(require_manager),
    db: AsyncSession = Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(501, "Stripe not configured")
    # TODO: Create Stripe Customer Portal session
    return {"message": "Stripe portal not yet implemented"}


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Stripe webhook handler — will process subscription events."""
    if not settings.stripe_webhook_secret:
        raise HTTPException(501, "Stripe webhooks not configured")
    # TODO: Verify signature and process events
    return {"status": "received"}


@router.get("/invoices")
async def list_invoices(
    user: User = Depends(require_manager),
):
    if not settings.stripe_secret_key:
        return []
    # TODO: Fetch invoices from Stripe
    return []
