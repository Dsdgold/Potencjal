"""BZP collector — fetches public procurement notices from ezamowienia.gov.pl.

API: https://ezamowienia.gov.pl/mo-board/api/v1/Board/Search
Searches for construction material tenders using CPV codes:
  - 44000000-44999999: Structures and materials; auxiliary products to construction
  - 45000000-45999999: Construction work
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.collectors.base import BaseCollector
from src.leads.models import Lead
from src.notifications.models import ScrapeJob

logger = logging.getLogger(__name__)

BZP_API = "https://ezamowienia.gov.pl/mo-board/api/v1/Board/Search"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# CPV codes related to construction materials
CPV_CONSTRUCTION = [
    "44100000",  # Construction materials and auxiliary items
    "44110000",  # Construction materials
    "44111000",  # Building materials
    "44200000",  # Structural products
    "44300000",  # Cable, wire and related products
    "45000000",  # Construction work
    "45200000",  # Works for complete or part construction
    "45300000",  # Building installation work
    "45400000",  # Building completion work
]

# Map CPV codes to material categories
CPV_TO_CATEGORY = {
    "441": "general",
    "442": "steel_metal",
    "443": "electrical",
    "450": "general",
    "451": "general",
    "452": "cement_concrete",
    "453": "plumbing",
    "454": "finishing",
}

# Polish voivodeships mapping from BZP location strings
VOIVODESHIP_KEYWORDS = {
    "mazowieckie": ["warszawa", "radom", "płock", "siedlce", "ostrołęka"],
    "małopolskie": ["kraków", "tarnów", "nowy sącz"],
    "śląskie": ["katowice", "częstochowa", "sosnowiec", "gliwice", "zabrze", "bielsko"],
    "wielkopolskie": ["poznań", "kalisz", "konin", "piła", "leszno"],
    "dolnośląskie": ["wrocław", "wałbrzych", "legnica", "jelenia góra"],
    "łódzkie": ["łódź", "piotrków", "skierniewice"],
    "pomorskie": ["gdańsk", "gdynia", "słupsk", "sopot"],
    "lubelskie": ["lublin", "chełm", "zamość", "biała podlaska"],
    "podkarpackie": ["rzeszów", "przemyśl", "krosno", "tarnobrzeg"],
    "kujawsko-pomorskie": ["bydgoszcz", "toruń", "włocławek", "grudziądz"],
    "zachodniopomorskie": ["szczecin", "koszalin", "stargard"],
    "warmińsko-mazurskie": ["olsztyn", "elbląg", "ełk"],
    "świętokrzyskie": ["kielce", "ostrowiec", "starachowice"],
    "podlaskie": ["białystok", "łomża", "suwałki"],
    "lubuskie": ["zielona góra", "gorzów"],
    "opolskie": ["opole", "nysa", "kędzierzyn"],
}


class BZPCollector(BaseCollector):
    """Fetches construction tenders from the BZP (Biuletyn Zamówień Publicznych)."""

    source = "bzp"

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, region_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.region_id = region_id

    async def collect(self) -> list[dict]:
        """Fetch recent construction-related tenders from BZP API."""
        all_notices: list[dict] = []

        for cpv in CPV_CONSTRUCTION:
            try:
                notices = await self._fetch_page(cpv)
                all_notices.extend(notices)
            except Exception as exc:
                logger.warning("BZP fetch failed for CPV %s: %s", cpv, exc)

        # Deduplicate by notice ID
        seen = set()
        unique = []
        for n in all_notices:
            nid = n.get("id") or n.get("noticeId", "")
            if nid and nid not in seen:
                seen.add(nid)
                unique.append(n)

        return unique

    async def _fetch_page(self, cpv_code: str, page: int = 0, size: int = 50) -> list[dict]:
        """Fetch a page of notices from BZP API for a given CPV code."""
        payload = {
            "cpvCode": cpv_code,
            "publicationDateFrom": _days_ago(7),
            "publicationDateTo": _today(),
            "orderType": "SUPPLY",
            "page": page,
            "size": size,
            "sortField": "publicationDate",
            "sortDirection": "DESC",
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(BZP_API, json=payload)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()

        return data.get("content", data.get("notices", []))

    async def parse(self, raw_data: dict) -> dict:
        """Parse a single BZP notice into a Lead-compatible dict."""
        notice_id = str(raw_data.get("id") or raw_data.get("noticeId", ""))
        title = raw_data.get("objectContract", {}).get("title", {}).get("text", "") or raw_data.get("title", "")
        description = raw_data.get("objectContract", {}).get("description", {}).get("text", "") or raw_data.get("description", "")

        # Extract contracting authority
        body = raw_data.get("contractingBody", {}) or raw_data.get("buyer", {})
        org_name = body.get("officialName", "") or body.get("name", "")
        contact = body.get("contactPoint", {}) or {}
        contact_person = contact.get("contactPerson", "") or contact.get("name", "")
        contact_phone = contact.get("phone", "")
        contact_email = contact.get("email", "")

        # Location
        city = body.get("city", "") or _extract_city_from_address(body.get("address", ""))

        # CPV codes
        cpv_list = []
        cpv_main = raw_data.get("objectContract", {}).get("cpvMain", {})
        if cpv_main:
            cpv_list.append(cpv_main.get("code", ""))
        for item in raw_data.get("objectContract", {}).get("cpvAdditional", []):
            cpv_list.append(item.get("code", ""))
        if not cpv_list:
            cpv_list = raw_data.get("cpvCodes", [])

        # Category from CPV
        category = _cpv_to_category(cpv_list[0] if cpv_list else "")

        # Estimated value
        value = raw_data.get("objectContract", {}).get("val", {})
        estimated_value = None
        if isinstance(value, dict):
            estimated_value = value.get("total") or value.get("low")
        elif isinstance(value, (int, float)):
            estimated_value = float(value)
        if not estimated_value:
            estimated_value = raw_data.get("estimatedValue")

        # Deadline
        deadline_str = raw_data.get("tenderDeadline") or raw_data.get("deadline", "")
        deadline = _parse_date(deadline_str)

        # NIP extraction from org
        nip = raw_data.get("contractingBody", {}).get("nip") or raw_data.get("buyer", {}).get("nip")

        # Voivodeship
        voivodeship = _guess_voivodeship(city)

        return {
            "source": "bzp",
            "source_id": notice_id,
            "name": org_name or title[:300],
            "title": title[:500] if title else None,
            "description": description[:5000] if description else None,
            "city": city or None,
            "voivodeship": voivodeship,
            "nip": nip,
            "contact_company": org_name or None,
            "contact_person": contact_person or None,
            "contact_phone": contact_phone or None,
            "contact_email": contact_email or None,
            "cpv_codes": [c for c in cpv_list if c],
            "category": category,
            "estimated_value": estimated_value,
            "deadline": deadline,
            "raw_data": raw_data,
            "status": "new",
        }

    async def run(self) -> ScrapeJob:
        """Full pipeline: fetch → parse → dedupe → store → return job summary."""
        job = ScrapeJob(source="bzp", status="running", started_at=datetime.now(timezone.utc))
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        try:
            raw_notices = await self.collect()
            leads_created = 0

            for raw in raw_notices:
                parsed = await self.parse(raw)
                source_id = parsed.get("source_id")

                # Skip duplicates
                if source_id:
                    existing = await self.db.execute(
                        select(Lead).where(
                            Lead.tenant_id == self.tenant_id,
                            Lead.source == "bzp",
                            Lead.source_id == source_id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                # Create lead
                lead = Lead(
                    tenant_id=self.tenant_id,
                    region_id=self.region_id,
                    **parsed,
                )
                self.db.add(lead)
                leads_created += 1

            await self.db.commit()

            job.status = "completed"
            job.items_found = len(raw_notices)
            job.items_qualified = leads_created
            job.finished_at = datetime.now(timezone.utc)

        except Exception as exc:
            job.status = "failed"
            job.error_log = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            logger.error("BZP collector failed: %s", exc)

        await self.db.commit()
        await self.db.refresh(job)
        return job


# ── Helpers ───────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _extract_city_from_address(address: str) -> str:
    if not address:
        return ""
    import re
    parts = [p.strip() for p in address.split(",")]
    for part in reversed(parts):
        # Remove Polish postal code (XX-XXX) and clean up
        cleaned = re.sub(r"\d{2}-\d{3}", "", part).strip()
        if cleaned and not any(ch.isdigit() for ch in cleaned):
            return cleaned
    return ""


def _cpv_to_category(cpv: str) -> str:
    if not cpv:
        return "general"
    for prefix, cat in CPV_TO_CATEGORY.items():
        if cpv.startswith(prefix):
            return cat
    return "general"


def _guess_voivodeship(city: str) -> str | None:
    if not city:
        return None
    city_lower = city.lower().strip()
    for voiv, cities in VOIVODESHIP_KEYWORDS.items():
        for c in cities:
            if c in city_lower or city_lower in c:
                return voiv
    return None
