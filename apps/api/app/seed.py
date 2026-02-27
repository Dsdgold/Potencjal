"""Seed database with initial plans and demo data."""

import asyncio
from sqlalchemy import select
from app.database import async_session, engine, Base
from app.models.organization import Organization, Plan
from app.models.user import User
from app.services.auth import hash_password
import structlog

logger = structlog.get_logger()

PLANS = [
    {
        "code": "free",
        "name": "Free (Trial)",
        "price_monthly": 0,
        "limits_json": {
            "lookups_per_month": 10,
            "max_users": 1,
            "max_watchlist": 5,
        },
        "features_json": {
            "basic_scoring": True,
            "credit_limit": True,
            "material_recommendation": False,
            "export_pdf": False,
            "notes": True,
            "tasks": False,
            "alerts": False,
            "api_access": False,
            "gus_connector": False,
            "ceidg_connector": False,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "price_monthly": 29900,  # 299 PLN
        "limits_json": {
            "lookups_per_month": 200,
            "max_users": 5,
            "max_watchlist": 50,
        },
        "features_json": {
            "basic_scoring": True,
            "credit_limit": True,
            "material_recommendation": True,
            "export_pdf": True,
            "notes": True,
            "tasks": True,
            "alerts": True,
            "api_access": False,
            "gus_connector": True,
            "ceidg_connector": True,
        },
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "price_monthly": 99900,  # 999 PLN
        "limits_json": {
            "lookups_per_month": 5000,
            "max_users": -1,  # unlimited
            "max_watchlist": -1,
        },
        "features_json": {
            "basic_scoring": True,
            "credit_limit": True,
            "material_recommendation": True,
            "export_pdf": True,
            "notes": True,
            "tasks": True,
            "alerts": True,
            "api_access": True,
            "gus_connector": True,
            "ceidg_connector": True,
            "sso": True,
            "custom_scoring": True,
        },
    },
]


async def seed():
    async with async_session() as session:
        # Seed plans
        for plan_data in PLANS:
            existing = await session.execute(
                select(Plan).where(Plan.code == plan_data["code"])
            )
            if not existing.scalar_one_or_none():
                session.add(Plan(**plan_data))
                logger.info("seeded_plan", code=plan_data["code"])

        await session.commit()

        # Seed demo user
        existing_user = await session.execute(
            select(User).where(User.email == "demo@sig.pl")
        )
        if not existing_user.scalar_one_or_none():
            # Get pro plan
            plan_result = await session.execute(select(Plan).where(Plan.code == "pro"))
            pro_plan = plan_result.scalar_one_or_none()

            org = Organization(name="SIG Demo", plan_id=pro_plan.id if pro_plan else None)
            session.add(org)
            await session.flush()

            user = User(
                org_id=org.id,
                email="demo@sig.pl",
                password_hash=hash_password("demo1234"),
                full_name="Demo User",
                role="admin",
            )
            session.add(user)

            # Superadmin
            superadmin = User(
                org_id=org.id,
                email="admin@sig.pl",
                password_hash=hash_password("admin1234"),
                full_name="Super Admin",
                role="superadmin",
            )
            session.add(superadmin)

            await session.commit()
            logger.info("seeded_demo_users")

    logger.info("seed_complete")


if __name__ == "__main__":
    asyncio.run(seed())
