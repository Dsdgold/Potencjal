"""AI Chat endpoint — local Ollama-powered assistant for lead analysis.

Provides context-aware AI responses about company data without external API costs.
Uses a small model (qwen2.5:1.5b) running locally via Ollama.
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user
from src.database import get_db
from src.leads.service import get_lead
from src.qualifier.ollama_client import generate, is_available
from src.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

AI_MODEL = "qwen2.5:1.5b"

SYSTEM_PROMPT = """Jesteś asystentem AI w platformie BuildLeads — narzędziu do oceny potencjału klientów B2B w branży materiałów budowlanych w Polsce.

Odpowiadaj po polsku, krótko i konkretnie. Bazuj WYŁĄCZNIE na danych firmy podanych w kontekście.
Możesz:
- Analizować potencjał sprzedażowy firmy
- Sugerować strategię kontaktu
- Wyjaśniać scoring i dane rejestrowe
- Rekomendować produkty/kategorie na podstawie PKD
- Porównywać z benchmarkami branżowymi

Nie wymyślaj danych których nie masz. Jeśli brakuje informacji, powiedz o tym."""


class ChatRequest(BaseModel):
    message: str
    lead_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    available: bool


@router.get("/status")
async def ai_status():
    """Check if AI assistant is available."""
    available = await is_available()
    return {"available": available, "model": AI_MODEL}


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with AI about a lead or general sales questions."""
    available = await is_available()
    if not available:
        raise HTTPException(503, "Asystent AI nie jest dostępny — Ollama nie uruchomiony")

    # Build context from lead data if provided
    context = ""
    if req.lead_id:
        try:
            lead = await get_lead(db, uuid.UUID(req.lead_id), user)
            if lead:
                context = _build_lead_context(lead)
        except Exception:
            pass

    prompt = f"{SYSTEM_PROMPT}\n\n"
    if context:
        prompt += f"=== DANE FIRMY ===\n{context}\n\n"
    prompt += f"Pytanie użytkownika: {req.message}\n\nOdpowiedź:"

    try:
        reply = await generate(prompt, model=AI_MODEL)
        return ChatResponse(reply=reply.strip(), model=AI_MODEL, available=True)
    except Exception as exc:
        logger.warning("AI chat failed: %s", exc)
        raise HTTPException(502, f"Błąd AI: {str(exc)[:200]}")


def _build_lead_context(lead) -> str:
    """Build text context from lead data for AI prompt."""
    lines = []
    lines.append(f"Nazwa: {lead.name}")
    if lead.nip:
        lines.append(f"NIP: {lead.nip}")
    if lead.city:
        loc = lead.city
        if lead.voivodeship:
            loc += f", woj. {lead.voivodeship}"
        lines.append(f"Lokalizacja: {loc}")
    if lead.street:
        lines.append(f"Adres: {lead.street}, {lead.postal_code or ''} {lead.city or ''}")
    if lead.legal_form:
        lines.append(f"Forma prawna: {lead.legal_form}")
    if lead.pkd:
        lines.append(f"PKD: {lead.pkd} — {lead.pkd_desc or ''}")
    if lead.vat_status:
        lines.append(f"Status VAT: {lead.vat_status}")
    if lead.employees:
        lines.append(f"Pracownicy: ok. {lead.employees}")
    if lead.revenue_pln:
        lines.append(f"Przychód: {lead.revenue_pln / 1_000_000:.1f}M PLN ({lead.revenue_band or ''})")
    if lead.years_active:
        lines.append(f"Lata na rynku: {lead.years_active:.1f}")
    if lead.score is not None:
        lines.append(f"Score: {lead.score}/100, Tier: {lead.tier}")
    if lead.annual_potential:
        lines.append(f"Potencjał roczny: {lead.annual_potential:,} PLN")
    if lead.website:
        lines.append(f"Strona WWW: {lead.website}")
    if lead.contact_person:
        lines.append(f"Osoba kontaktowa: {lead.contact_person}")
    if lead.contact_email:
        lines.append(f"Email: {lead.contact_email}")
    if lead.contact_phone:
        lines.append(f"Telefon: {lead.contact_phone}")
    if lead.board_members:
        members = ", ".join(f"{m.get('name', '')} ({m.get('function', '')})" for m in lead.board_members[:5])
        lines.append(f"Zarząd: {members}")
    if lead.description:
        lines.append(f"Opis: {lead.description[:500]}")
    if lead.notes:
        lines.append(f"Notatki: {lead.notes[:300]}")
    return "\n".join(lines)
