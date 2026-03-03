"""Base collector class — all data collectors inherit from this.

Collectors are Celery tasks that:
1. Fetch data from external sources (BZP, GUNB, TED, KRS, portals)
2. Parse and normalize into Lead-compatible dicts
3. Store as new leads with source tracking
"""

from abc import ABC, abstractmethod


class BaseCollector(ABC):
    source: str  # e.g. "bzp", "gunb", "ted", "krs"

    @abstractmethod
    async def collect(self) -> list[dict]:
        """Fetch and return normalized lead dicts from the source."""
        ...

    @abstractmethod
    async def parse(self, raw_data: dict) -> dict:
        """Parse a single raw item into a Lead-compatible dict."""
        ...
