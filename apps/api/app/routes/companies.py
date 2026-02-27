"""Company lookup, notes, tasks, watchlist routes."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, CurrentUser
from app.models.company import Company
from app.models.crm import Note, Task, Watchlist
from app.models.organization import UsageEvent
from app.models.admin import AuditLog
from app.schemas.company import (
    NIPLookupRequest, NoteCreate, NoteResponse,
    TaskCreate, TaskResponse, WatchlistResponse,
)
from app.services.lookup import lookup_company
from app.utils.nip import validate_nip, clean_nip

router = APIRouter()


@router.post("/lookup")
async def lookup(
    req: NIPLookupRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    force: bool = Query(False, description="Force refresh from providers"),
):
    nip = clean_nip(req.nip)
    if not validate_nip(nip):
        raise HTTPException(status_code=422, detail="Nieprawidłowy NIP (błąd sumy kontrolnej)")

    # Usage tracking
    usage = UsageEvent(
        org_id=current_user.org_id,
        user_id=current_user.id,
        event_type="company_lookup",
        meta_json={"nip": nip, "purpose": req.purpose},
    )
    db.add(usage)

    # Audit log
    db.add(AuditLog(
        org_id=current_user.org_id,
        actor_user_id=current_user.id,
        action="company_lookup",
        target_type="company",
        target_id=nip,
        purpose=req.purpose,
    ))

    # Check if mock mode (dev)
    from app.config import get_settings
    use_mock = get_settings().ENVIRONMENT == "development"

    result = await lookup_company(
        nip=nip,
        db=db,
        org_id=current_user.org_id,
        user_id=current_user.id,
        force_refresh=force,
        use_mock=use_mock,
    )

    return result


@router.get("/search")
async def search_companies(
    q: str = Query(min_length=2),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search companies by NIP or name (within already looked-up companies)."""
    query = select(Company)
    if q.isdigit():
        query = query.where(Company.nip.contains(q))
    else:
        query = query.where(Company.name.ilike(f"%{q}%"))

    result = await db.execute(query.limit(20))
    companies = result.scalars().all()

    return [
        {
            "id": str(c.id), "nip": c.nip, "name": c.name,
            "legal_form": c.legal_form, "pkd_main": c.pkd_main,
        }
        for c in companies
    ]


@router.get("/{nip}")
async def get_company(
    nip: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get cached company profile (no new lookup)."""
    clean = clean_nip(nip)
    result = await db.execute(select(Company).where(Company.nip == clean))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Firma nie znaleziona — wykonaj lookup")

    from app.services.lookup import _build_profile_response, _get_fresh_snapshot
    snapshot = await _get_fresh_snapshot(db, company.id, 86400 * 30)  # 30 days for cached view
    if not snapshot:
        raise HTTPException(status_code=404, detail="Brak danych — wykonaj nowy lookup")

    return await _build_profile_response(db, company, snapshot, None)


# ── Notes ──────────────────────────────────────────

@router.post("/{nip}/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    nip: str, req: NoteCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(db, nip)
    note = Note(
        org_id=current_user.org_id,
        company_id=company.id,
        user_id=current_user.id,
        text=req.text,
        tags_json=req.tags,
    )
    db.add(note)
    await db.flush()
    return note


@router.get("/{nip}/notes", response_model=list[NoteResponse])
async def list_notes(
    nip: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(db, nip)
    result = await db.execute(
        select(Note)
        .where(Note.company_id == company.id, Note.org_id == current_user.org_id)
        .order_by(Note.created_at.desc())
    )
    return result.scalars().all()


# ── Tasks ──────────────────────────────────────────

@router.post("/{nip}/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    nip: str, req: TaskCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(db, nip)
    task = Task(
        org_id=current_user.org_id,
        company_id=company.id,
        title=req.title,
        description=req.description,
        assigned_user_id=req.assigned_user_id,
        due_at=req.due_at,
    )
    db.add(task)
    await db.flush()
    return task


@router.get("/{nip}/tasks", response_model=list[TaskResponse])
async def list_tasks(
    nip: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(db, nip)
    result = await db.execute(
        select(Task)
        .where(Task.company_id == company.id, Task.org_id == current_user.org_id)
        .order_by(Task.created_at.desc())
    )
    return result.scalars().all()


# ── Watchlist ──────────────────────────────────────

@router.post("/{nip}/watch", status_code=201)
async def add_to_watchlist(
    nip: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(db, nip)
    existing = await db.execute(
        select(Watchlist).where(
            Watchlist.company_id == company.id,
            Watchlist.org_id == current_user.org_id,
            Watchlist.user_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_watching"}

    db.add(Watchlist(org_id=current_user.org_id, company_id=company.id, user_id=current_user.id))
    return {"status": "added"}


@router.delete("/{nip}/watch")
async def remove_from_watchlist(
    nip: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company = await _get_company(db, nip)
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.company_id == company.id,
            Watchlist.org_id == current_user.org_id,
            Watchlist.user_id == current_user.id,
        )
    )
    watch = result.scalar_one_or_none()
    if watch:
        await db.delete(watch)
    return {"status": "removed"}


@router.get("/watchlist/all")
async def get_watchlist(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist, Company)
        .join(Company, Company.id == Watchlist.company_id)
        .where(Watchlist.org_id == current_user.org_id, Watchlist.user_id == current_user.id)
        .order_by(Watchlist.created_at.desc())
    )
    rows = result.all()
    return [
        {
            "id": str(w.id), "company_id": str(w.company_id),
            "company_name": c.name, "company_nip": c.nip,
            "created_at": w.created_at.isoformat(),
        }
        for w, c in rows
    ]


async def _get_company(db: AsyncSession, nip: str) -> Company:
    clean = clean_nip(nip)
    result = await db.execute(select(Company).where(Company.nip == clean))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Firma nie znaleziona")
    return company
