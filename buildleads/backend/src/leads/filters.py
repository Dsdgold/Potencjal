"""Query filter helpers for leads."""

import uuid
from datetime import datetime

from fastapi import Query


class LeadFilters:
    """Dependency that collects all lead query params."""

    def __init__(
        self,
        status: str | None = None,
        category: str | None = None,
        source: str | None = None,
        tier: str | None = None,
        city: str | None = None,
        pkd: str | None = None,
        q: str | None = None,
        region_id: uuid.UUID | None = None,
        score_min: int | None = None,
        score_max: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = Query(1, ge=1),
        per_page: int = Query(25, ge=1, le=200),
    ):
        self.status = status
        self.category = category
        self.source = source
        self.tier = tier
        self.city = city
        self.pkd = pkd
        self.q = q
        self.region_id = region_id
        self.score_min = score_min
        self.score_max = score_max
        self.date_from = date_from
        self.date_to = date_to
        self.page = page
        self.per_page = per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page
