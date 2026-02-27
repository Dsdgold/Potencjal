"""Base interface for all data provider connectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ProviderResult:
    provider_name: str
    success: bool
    raw_data: dict = field(default_factory=dict)
    normalized_data: dict = field(default_factory=dict)
    error: str | None = None
    fetched_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    fields_count: int = 0

    def __post_init__(self):
        if self.success and not self.fields_count:
            self.fields_count = sum(1 for v in self.normalized_data.values() if v is not None)


class BaseProvider(ABC):
    """Abstract base class for data provider connectors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name."""
        ...

    @property
    def required_credentials(self) -> list[str]:
        """List of credential keys required (empty = no auth needed)."""
        return []

    @property
    def is_feature_flagged(self) -> bool:
        """If True, requires explicit activation."""
        return False

    @abstractmethod
    async def fetch(self, nip: str, credentials: dict | None = None) -> ProviderResult:
        """
        Fetch raw data for a company by NIP.
        Must handle rate limits, timeouts, and errors gracefully.
        """
        ...

    @abstractmethod
    def normalize(self, raw_data: dict) -> dict:
        """
        Transform raw API response into normalized schema fields.
        Returns a partial dict matching SnapshotData fields.
        """
        ...
