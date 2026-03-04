"""AI Chat endpoint — Claude Haiku (primary) or Ollama (fallback).

Uses Anthropic API when ANTHROPIC_API_KEY is set, otherwise falls back to Ollama.
Daily query limit per user based on subscription plan.
Searches the web for current information before answering.
"""

import re
import uuid
import logging
from datetime import date
from html.parser import HTMLParser

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.permissions import get_current_user
from src.config import settings, PLAN_LIMITS, PlanType
from src.database import get_db
from src.leads.service import get_lead
from src.users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
OLLAMA_MODEL = "llama3.1:8b"

SYSTEM_PROMPT = f"""You are a Polish-speaking AI assistant for BuildLeads - a B2B sales lead assessment platform for construction materials in Poland.

Today's date is: {date.today().strftime('%d %B %Y')} (year {date.today().year}).

CRITICAL RULES:
1. ALWAYS respond in Polish language
2. Use the company data provided in context
3. Use web search results if available for current information
4. Analyze sales potential, suggest contact strategies
5. Recommend construction product categories based on PKD codes
6. If asked about the date, today is {date.today().strftime('%d.%m.%Y')}
7. Be concise and practical - focus on actionable insights
8. Never make up data you don't have"""


class ChatRequest(BaseModel):
    message: str
    lead_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str
    available: bool
    web_sources: list[str] | None = None
    queries_used: int = 0
    queries_limit: int = 0


# ── Rate limiting ──

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _get_daily_limit(user: User) -> int:
    """Get AI queries per day limit for user's plan."""
    try:
        plan = PlanType(user.plan)
    except ValueError:
        plan = PlanType.STARTER
    return PLAN_LIMITS.get(plan, {}).get("ai_queries_per_day", 10)


def _redis_key(user_id: str) -> str:
    """Redis key for daily AI usage counter."""
    today = date.today().isoformat()
    return f"ai_usage:{user_id}:{today}"


async def _check_and_increment(user: User) -> tuple[int, int]:
    """Check rate limit and increment counter. Returns (used, limit).

    Raises HTTPException 429 if limit exceeded.
    """
    limit = _get_daily_limit(user)
    if limit == -1:  # unlimited
        return 0, -1

    r = await _get_redis()
    key = _redis_key(str(user.id))

    used = await r.get(key)
    used = int(used) if used else 0

    if used >= limit:
        plan_name = user.plan or "starter"
        raise HTTPException(
            429,
            f"Osiagnieto dzienny limit {limit} zapytan AI (pakiet {plan_name}). "
            f"Zmien pakiet na wyzszy, aby uzyskac wiecej zapytan."
        )

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 86400)  # 24h TTL
    await pipe.execute()

    return used + 1, limit


async def _get_usage(user: User) -> tuple[int, int]:
    """Get current usage without incrementing."""
    limit = _get_daily_limit(user)
    if limit == -1:
        return 0, -1
    try:
        r = await _get_redis()
        key = _redis_key(str(user.id))
        used = await r.get(key)
        return int(used) if used else 0, limit
    except Exception:
        return 0, limit


# ── AI backends ──

def _has_claude() -> bool:
    return bool(settings.anthropic_api_key)


async def _claude_chat(system: str, user_content: str) -> str:
    """Call Anthropic Messages API."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": CLAUDE_MODEL,
                "max_tokens": 1024,
                "system": system,
                "messages": [{"role": "user", "content": user_content}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _ollama_available() -> bool:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def _ollama_chat(system: str, user_content: str) -> str:
    """Call Ollama chat API."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


# ── Web search ──

class _TextExtractor(HTMLParser):
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
        return " ".join(self._text)[:limit]


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
            urls = []
            for m in re.finditer(r'href="/url\?q=([^&"]+)', html):
                url = m.group(1)
                if url.startswith("http") and "google" not in url:
                    urls.append(url)

            parser = _TextExtractor()
            try:
                parser.feed(html)
            except Exception:
                pass

            body = parser.get_text(3000)
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

    queries.append(f"{base} {user_question}")
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

    seen = set()
    unique_urls = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    combined = "\n---\n".join(all_text)
    return combined[:4000], unique_urls[:5]


# ── Endpoints ──

@router.get("/status")
async def ai_status(user: User = Depends(get_current_user)):
    """Check if AI assistant is available + usage info."""
    used, limit = await _get_usage(user)
    if _has_claude():
        return {
            "available": True,
            "model": CLAUDE_MODEL,
            "provider": "claude",
            "queries_used": used,
            "queries_limit": limit,
        }
    ollama_ok = await _ollama_available()
    return {
        "available": ollama_ok,
        "model": OLLAMA_MODEL,
        "provider": "ollama",
        "queries_used": used,
        "queries_limit": limit,
    }


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with AI about a lead, with web search for current data."""
    use_claude = _has_claude()

    if not use_claude:
        ollama_ok = await _ollama_available()
        if not ollama_ok:
            raise HTTPException(503, "Asystent AI nie jest dostepny — brak klucza Anthropic i Ollama nie uruchomiony")

    # Check daily rate limit (raises 429 if exceeded)
    used, limit = await _check_and_increment(user)

    # Build context from lead data
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
        web_text, web_sources = await _web_search(req.message)

    # Build user message with context
    user_content = ""
    if lead_context:
        user_content += f"=== DANE FIRMY Z BAZY ===\n{lead_context}\n\n"
    if web_text:
        user_content += f"=== WYNIKI WYSZUKIWANIA INTERNETOWEGO ===\n{web_text}\n\n"
    user_content += f"Pytanie: {req.message}"

    # Call AI
    model_name = CLAUDE_MODEL if use_claude else OLLAMA_MODEL
    try:
        if use_claude:
            reply = await _claude_chat(SYSTEM_PROMPT, user_content)
        else:
            reply = await _ollama_chat(SYSTEM_PROMPT, user_content)

        return ChatResponse(
            reply=reply.strip(),
            model=model_name,
            available=True,
            web_sources=web_sources if web_sources else None,
            queries_used=used,
            queries_limit=limit,
        )
    except Exception as exc:
        logger.warning("AI chat failed (%s): %s", model_name, exc)
        # If Claude fails, try Ollama as fallback
        if use_claude:
            try:
                ollama_ok = await _ollama_available()
                if ollama_ok:
                    reply = await _ollama_chat(SYSTEM_PROMPT, user_content)
                    return ChatResponse(
                        reply=reply.strip(),
                        model=OLLAMA_MODEL,
                        available=True,
                        web_sources=web_sources if web_sources else None,
                        queries_used=used,
                        queries_limit=limit,
                    )
            except Exception:
                pass
        raise HTTPException(502, f"Blad AI: {str(exc)[:200]}")


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
        lines.append(f"Przychod: {lead.revenue_pln / 1_000_000:.1f}M PLN ({lead.revenue_band or ''})")
    if lead.years_active:
        lines.append(f"Lata na rynku: {lead.years_active:.1f}")
    if lead.score is not None:
        lines.append(f"Score: {lead.score}/100, Tier: {lead.tier}")
    if lead.annual_potential:
        lines.append(f"Potencjal roczny: {lead.annual_potential:,} PLN")
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
            lines.append(f"Zarzad: {members}")
    if lead.description:
        lines.append(f"Opis: {lead.description[:500]}")
    if lead.notes:
        lines.append(f"Notatki: {lead.notes[:300]}")
    return "\n".join(lines)
