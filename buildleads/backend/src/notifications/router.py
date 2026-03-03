"""Notification endpoints — list, read, unread count."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user
from src.database import get_db
from src.notifications.models import Notification
from src.users.models import User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "read": n.read,
            "lead_id": str(n.lead_id) if n.lead_id else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.get("/unread-count")
async def unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    count = (await db.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read == False)  # noqa: E712
    )).scalar() or 0
    return {"count": count}


@router.patch("/{notif_id}/read")
async def mark_read(
    notif_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif = await db.get(Notification, notif_id)
    if not notif or notif.user_id != user.id:
        raise HTTPException(404, "Not found")
    notif.read = True
    await db.commit()
    return {"status": "ok"}


@router.post("/read-all")
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read == False)  # noqa: E712
        .values(read=True)
    )
    await db.commit()
    return {"status": "ok"}
