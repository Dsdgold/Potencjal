"""GUNB collector — fetches building permits from wyszukiwarka.gunb.gov.pl.

GUNB (Główny Urząd Nadzoru Budowlanego) publishes building permits data.
The search API at wyszukiwarka.gunb.gov.pl allows querying by voivodeship,
category, and date range.

This collector focuses on construction projects that indicate potential
demand for construction materials.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.collectors.base import BaseCollector
from src.leads.models import Lead
from src.notifications.models import ScrapeJob

logger = logging.getLogger(__name__)

GUNB_SEARCH_URL = "https://wyszukiwarka.gunb.gov.pl/api/search"
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# GUNB construction categories relevant to material sales
GUNB_CATEGORIES = [
    "budynek mieszkalny jednorodzinny",
    "budynek mieszkalny wielorodzinny",
    "budynek użyteczności publicznej",
    "budynek przemysłowy",
    "budynek magazynowy",
    "budynek handlowy",
    "budynek biurowy",
    "obiekt infrastruktury",
]

# Map GUNB categories to MaterialCategory
CATEGORY_MAP = {
    "budynek mieszkalny jednorodzinny": "general",
    "budynek mieszkalny wielorodzinny": "cement_concrete",
    "budynek użyteczności publicznej": "finishing",
    "budynek przemysłowy": "steel_metal",
    "budynek magazynowy": "steel_metal",
    "budynek handlowy": "finishing",
    "budynek biurowy": "finishing",
    "obiekt infrastruktury": "cement_concrete",
}

# Voivodeship codes used by GUNB
VOIVODESHIP_CODES = {
    "02": "dolnośląskie",
    "04": "kujawsko-pomorskie",
    "06": "lubelskie",
    "08": "lubuskie",
    "10": "łódzkie",
    "12": "małopolskie",
    "14": "mazowieckie",
    "16": "opolskie",
    "18": "podkarpackie",
    "20": "podlaskie",
    "22": "pomorskie",
    "24": "śląskie",
    "26": "świętokrzyskie",
    "28": "warmińsko-mazurskie",
    "30": "wielkopolskie",
    "32": "zachodniopomorskie",
}


class GUNBCollector(BaseCollector):
    """Fetches building permits from GUNB registry."""

    source = "gunb"

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        region_id: uuid.UUID | None = None,
        voivodeships: list[str] | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.region_id = region_id
        self.voivodeships = voivodeships  # Filter to specific voivodeships

    async def collect(self) -> list[dict]:
        """Fetch recent building permits from GUNB."""
        all_permits: list[dict] = []
        date_from = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
        date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Determine which voivodeships to search
        voiv_codes = VOIVODESHIP_CODES.keys()
        if self.voivodeships:
            voiv_codes = [
                code for code, name in VOIVODESHIP_CODES.items()
                if name in self.voivodeships
            ]

        for voiv_code in voiv_codes:
            try:
                permits = await self._fetch_permits(voiv_code, date_from, date_to)
                all_permits.extend(permits)
            except Exception as exc:
                voiv_name = VOIVODESHIP_CODES.get(voiv_code, voiv_code)
                logger.warning("GUNB fetch failed for %s: %s", voiv_name, exc)

        return all_permits

    async def _fetch_permits(
        self, voivodeship_code: str, date_from: str, date_to: str
    ) -> list[dict]:
        """Fetch building permits for a specific voivodeship."""
        params = {
            "wojewodztwo": voivodeship_code,
            "dataOd": date_from,
            "dataDo": date_to,
            "page": 0,
            "size": 100,
        }

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(GUNB_SEARCH_URL, params=params)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()

        # Tag each permit with the voivodeship
        permits = data.get("content", data.get("results", []))
        voiv_name = VOIVODESHIP_CODES.get(voivodeship_code, "")
        for p in permits:
            p["_voivodeship"] = voiv_name
            p["_voivodeship_code"] = voivodeship_code
        return permits

    async def parse(self, raw_data: dict) -> dict:
        """Parse a single GUNB building permit into a Lead-compatible dict."""
        permit_id = str(raw_data.get("id") or raw_data.get("numerDecyzji", ""))

        # Investor info (potential buyer of construction materials)
        investor = raw_data.get("inwestor", {}) or {}
        investor_name = investor.get("nazwa", "") or investor.get("imieNazwisko", "")
        investor_nip = investor.get("nip")

        # Location
        location = raw_data.get("lokalizacja", {}) or raw_data.get("adres", {}) or {}
        city = location.get("miejscowosc", "") or location.get("miasto", "")
        street = location.get("ulica", "")
        voivodeship = raw_data.get("_voivodeship", "")

        # Construction category
        object_type = raw_data.get("rodzajObiektu", "") or raw_data.get("kategoriaObiektu", "")
        category = "general"
        for gunb_cat, mat_cat in CATEGORY_MAP.items():
            if gunb_cat in object_type.lower():
                category = mat_cat
                break

        # Permit details
        permit_date = raw_data.get("dataDecyzji") or raw_data.get("dataWydania", "")
        description = raw_data.get("opisInwestycji", "") or raw_data.get("opis", "")
        title = f"Pozwolenie na budowę: {object_type}" if object_type else "Pozwolenie na budowę"

        # Estimated value from area (rough heuristic: area * avg cost/m2)
        area = raw_data.get("powierzchnia") or raw_data.get("powierzchniaUzytkowa")
        estimated_value = None
        if area and isinstance(area, (int, float)):
            # Rough material cost estimate: 800-1500 PLN/m2 for materials
            estimated_value = float(area) * 1000

        return {
            "source": "gunb",
            "source_id": permit_id,
            "name": investor_name or title[:300],
            "title": title[:500],
            "description": description[:5000] if description else None,
            "nip": investor_nip,
            "city": city or None,
            "voivodeship": voivodeship or None,
            "category": category,
            "estimated_value": estimated_value,
            "contact_company": investor_name or None,
            "raw_data": raw_data,
            "status": "new",
        }

    async def run(self) -> ScrapeJob:
        """Full pipeline: fetch → parse → dedupe → store → return job summary."""
        job = ScrapeJob(source="gunb", status="running", started_at=datetime.now(timezone.utc))
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        try:
            raw_permits = await self.collect()
            leads_created = 0

            for raw in raw_permits:
                parsed = await self.parse(raw)
                source_id = parsed.get("source_id")

                # Skip duplicates
                if source_id:
                    existing = await self.db.execute(
                        select(Lead).where(
                            Lead.tenant_id == self.tenant_id,
                            Lead.source == "gunb",
                            Lead.source_id == source_id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                lead = Lead(
                    tenant_id=self.tenant_id,
                    region_id=self.region_id,
                    **parsed,
                )
                self.db.add(lead)
                leads_created += 1

            await self.db.commit()

            job.status = "completed"
            job.items_found = len(raw_permits)
            job.items_qualified = leads_created
            job.finished_at = datetime.now(timezone.utc)

        except Exception as exc:
            job.status = "failed"
            job.error_log = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            logger.error("GUNB collector failed: %s", exc)

        await self.db.commit()
        await self.db.refresh(job)
        return job
