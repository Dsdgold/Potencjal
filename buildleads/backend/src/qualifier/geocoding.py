"""Geocoding via OpenStreetMap Nominatim (free, no API key required).

Converts addresses to latitude/longitude coordinates for map display.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)
TIMEOUT = httpx.Timeout(10.0, connect=5.0)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


@dataclass
class GeoResult:
    latitude: float | None = None
    longitude: float | None = None
    display_name: str | None = None
    error: str | None = None


async def geocode_address(
    city: str | None = None,
    street: str | None = None,
    postal_code: str | None = None,
    company_name: str | None = None,
) -> GeoResult:
    """Geocode a Polish address using Nominatim.

    Tries multiple query strategies:
    1. Full address (street + city + postal_code)
    2. City + postal_code
    3. City only
    """
    if not city:
        return GeoResult(error="no_city")

    queries = []

    # Strategy 1: Full address
    if street:
        full = f"{street}, {postal_code + ' ' if postal_code else ''}{city}, Polska"
        queries.append(full)

    # Strategy 2: City + postal code
    if postal_code:
        queries.append(f"{postal_code} {city}, Polska")

    # Strategy 3: City only
    queries.append(f"{city}, Polska")

    async with httpx.AsyncClient(
        timeout=TIMEOUT,
        headers={
            "User-Agent": "BuildLeads/2.0 (https://buildleads.pl; contact@buildleads.pl)",
        },
    ) as client:
        for query in queries:
            try:
                resp = await client.get(
                    NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "countrycodes": "pl",
                    },
                )
                if resp.status_code != 200:
                    continue

                results = resp.json()
                if results and len(results) > 0:
                    hit = results[0]
                    return GeoResult(
                        latitude=float(hit["lat"]),
                        longitude=float(hit["lon"]),
                        display_name=hit.get("display_name", ""),
                    )

            except Exception as exc:
                logger.warning("Geocoding failed for query '%s': %s", query, exc)

    return GeoResult(error="not_found")
