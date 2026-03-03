"""Notification creation helpers."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.models import Notification


async def create_notification(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    type: str,
    title: str,
    message: str | None = None,
    lead_id: uuid.UUID | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        tenant_id=tenant_id,
        type=type,
        title=title,
        message=message,
        lead_id=lead_id,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif
