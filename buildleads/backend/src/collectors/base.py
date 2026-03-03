"""Base collector class — all data collectors inherit from this.

Collectors are background tasks that:
1. Fetch data from external sources (BZP, GUNB, TED, KRS, portals)
2. Parse and normalize into Lead-compatible dicts
3. Deduplicate against existing leads (by source + source_id)
4. Store as new leads with source tracking
5. Log results to ScrapeJob table
"""

from abc import ABC, abstractmethod

from src.notifications.models import ScrapeJob


class BaseCollector(ABC):
    source: str  # e.g. "bzp", "gunb", "ted", "krs"

    @abstractmethod
    async def collect(self) -> list[dict]:
        """Fetch and return raw data items from the source."""
        ...

    @abstractmethod
    async def parse(self, raw_data: dict) -> dict:
        """Parse a single raw item into a Lead-compatible dict."""
        ...

    @abstractmethod
    async def run(self) -> ScrapeJob:
        """Full pipeline: collect → parse → dedupe → store → ScrapeJob."""
        ...
