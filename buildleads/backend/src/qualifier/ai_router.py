"""AI Chat endpoint — Ollama-powered assistant with web search for lead analysis.

Uses gemma2:9b for Polish language support.
Searches the web for current information before answering.
"""

import re
import uuid
import logging
from datetime import date
from html.parser import HTMLParser

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user
from src.database import get_db
from src.leads.service import get_lead
from src.qualifier.ollama_client import chat, is_available
from src.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

AI_MODEL = "gemma2:9b"

SYSTEM_PROMPT = f"""Jesteś asystentem AI w platformie BuildLeads — narzędziu do oceny potencjału klientów B2B w branży materiałów budowlanych w Polsce.
Dzisiejsza data: {date.today().isoformat()}.

Zasady:
- Odpowiadaj ZAWSZE po polsku, krótko i konkretnie
- Bazuj na danych firmy z kontekstu ORAZ na wynikach wyszukiwania internetowego
- Analizuj potencjał sprzedażowy, sugeruj strategię kontaktu
- Wyjaśniaj scoring i dane rejestrowe
- Rekomenduj produkty/kategorie budowlane na podstawie PKD
- Jeśli masz wyniki wyszukiwania, wykorzystaj je do aktualnych informacji
- Nie wymyślaj danych których nie masz"""


class ChatRequest(BaseModel):
    message: str
    lead_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    available: bool
    web_sources: list[str] | None = None


class _TextExtractor(HTMLParser):
    """Extract visible text from HTML."""

    def __init__(self):
        super().__init__()
        self._text: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            t = data.strip()
            if t:
                self._text.append(t)

    def get_text(self, limit: int = 3000) -> str:
        full = " ".join(self._text)
        return full[:limit]


async def _web_search(query: str, num: int = 5) -> tuple[str, list[str]]:
    """Search Google and return extracted text + source URLs."""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "pl,en;q=0.5",
            },
        ) as client:
            resp = await client.get(
                "https://www.google.com/search",
                params={"q": query, "hl": "pl", "num": num, "gl": "pl"},
            )
            if resp.status_code != 200:
                return "", []

            html = resp.text

            # Extract URLs from search results
            urls = []
            for m in re.finditer(r'href="/url\?q=([^&"]+)', html):
                url = m.group(1)
                if url.startswith("http") and "google" not in url:
                    urls.append(url)

            # Extract text snippets
            parser = _TextExtractor()
            try:
                parser.feed(html)
            except Exception:
                pass

            body = parser.get_text(3000)
            # Remove Google boilerplate
            body = re.sub(
                r"(Szukaj|Ustawienia|Narzędzia|Wszystkie|Grafika|Filmy|Więcej|"
                r"Zaloguj się|Zaawansowane|Preferencje|Filtruj|Google)[\s,]*",
                "", body,
            )

            return body, urls[:5]

    except Exception as exc:
        logger.warning("Web search failed: %s", exc)
        return "", []


async def _search_for_lead(company_name: str, nip: str | None, city: str | None, user_question: str) -> tuple[str, list[str]]:
    """Run multiple web searches about a company and merge results."""
    import asyncio

    queries = []
    base = company_name
    if city:
        base += f" {city}"

    # Search 1: company + user's question
    queries.append(f"{base} {user_question}")
    # Search 2: company general info
    if nip:
        queries.append(f"{company_name} NIP {nip}")
    else:
        queries.append(f"{base} firma")

    results = await asyncio.gather(*[_web_search(q, num=3) for q in queries], return_exceptions=True)

    all_text = []
    all_urls = []
    for r in results:
        if isinstance(r, Exception):
            continue
        text, urls = r
        if text:
            all_text.append(text)
        all_urls.extend(urls)

    # Deduplicate URLs
    seen = set()
    unique_urls = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    combined = "\n---\n".join(all_text)
    # Trim to reasonable size for context
    return combined[:4000], unique_urls[:5]


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
    """Chat with AI about a lead, with web search for current data."""
    available = await is_available()
    if not available:
        raise HTTPException(503, "Asystent AI nie jest dostępny — Ollama nie uruchomiony")

    # Build context from lead data if provided
    lead_context = ""
    company_name = ""
    nip = ""
    city = ""
    if req.lead_id:
        try:
            lead = await get_lead(db, uuid.UUID(req.lead_id), user)
            if lead:
                lead_context = _build_lead_context(lead)
                company_name = lead.name or ""
                nip = lead.nip or ""
                city = lead.city or ""
        except Exception:
            pass

    # Web search for current info
    web_text = ""
    web_sources: list[str] = []
    if company_name:
        web_text, web_sources = await _search_for_lead(
            company_name, nip, city, req.message
        )
    else:
        # General question — search directly
        web_text, web_sources = await _web_search(req.message)

    # Build chat messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_content = ""
    if lead_context:
        user_content += f"=== DANE FIRMY Z BAZY ===\n{lead_context}\n\n"
    if web_text:
        user_content += f"=== WYNIKI WYSZUKIWANIA INTERNETOWEGO ===\n{web_text}\n\n"
    user_content += f"Pytanie: {req.message}"

    messages.append({"role": "user", "content": user_content})

    try:
        reply = await chat(messages, model=AI_MODEL)
        return ChatResponse(
            reply=reply.strip(),
            model=AI_MODEL,
            available=True,
            web_sources=web_sources if web_sources else None,
        )
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
        members = ", ".join(
            f"{m.get('name', '')} ({m.get('function', '')})"
            for m in lead.board_members[:5]
            if "*" not in m.get("name", "")
        )
        if members:
            lines.append(f"Zarząd: {members}")
    if lead.description:
        lines.append(f"Opis: {lead.description[:500]}")
    if lead.notes:
        lines.append(f"Notatki: {lead.notes[:300]}")
    return "\n".join(lines)
