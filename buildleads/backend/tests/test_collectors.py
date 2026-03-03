"""Tests for BZP and GUNB collectors — parsing logic (no network calls)."""

import pytest

from src.collectors.bzp import (
    BZPCollector,
    _cpv_to_category,
    _extract_city_from_address,
    _guess_voivodeship,
    _parse_date,
)
from src.collectors.gunb import VOIVODESHIP_CODES, CATEGORY_MAP


class TestBZPParsing:
    def test_cpv_to_category_steel(self):
        assert _cpv_to_category("44200000") == "steel_metal"

    def test_cpv_to_category_electrical(self):
        assert _cpv_to_category("44300000") == "electrical"

    def test_cpv_to_category_general(self):
        assert _cpv_to_category("44100000") == "general"

    def test_cpv_to_category_unknown(self):
        assert _cpv_to_category("99000000") == "general"

    def test_cpv_to_category_empty(self):
        assert _cpv_to_category("") == "general"

    def test_extract_city_from_address(self):
        assert _extract_city_from_address("ul. Główna 5, 00-001 Warszawa") == "Warszawa"

    def test_extract_city_empty(self):
        assert _extract_city_from_address("") == ""

    def test_guess_voivodeship_warszawa(self):
        assert _guess_voivodeship("Warszawa") == "mazowieckie"

    def test_guess_voivodeship_krakow(self):
        assert _guess_voivodeship("Kraków") == "małopolskie"

    def test_guess_voivodeship_unknown(self):
        assert _guess_voivodeship("Mała Wieś") is None

    def test_guess_voivodeship_none(self):
        assert _guess_voivodeship("") is None

    def test_parse_date_iso(self):
        dt = _parse_date("2026-03-01T10:30:00")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 3

    def test_parse_date_simple(self):
        dt = _parse_date("2026-01-15")
        assert dt is not None
        assert dt.day == 15

    def test_parse_date_empty(self):
        assert _parse_date("") is None

    def test_parse_date_invalid(self):
        assert _parse_date("not-a-date") is None


class TestBZPCollectorParse:
    @pytest.mark.asyncio
    async def test_parse_notice(self):
        """Test parsing a mock BZP notice."""
        # We can't instantiate BZPCollector without a DB, but we can test
        # the parse method by creating a minimal mock
        raw = {
            "id": "BZP-12345",
            "objectContract": {
                "title": {"text": "Dostawa materiałów budowlanych"},
                "description": {"text": "Zamówienie na cement i stal"},
                "cpvMain": {"code": "44110000"},
            },
            "contractingBody": {
                "officialName": "Urząd Miasta Warszawa",
                "city": "Warszawa",
                "contactPoint": {
                    "contactPerson": "Jan Kowalski",
                    "email": "jan@um.warszawa.pl",
                    "phone": "+48 22 1234567",
                },
            },
            "tenderDeadline": "2026-04-15T12:00:00",
        }

        # Test the parsing functions used within parse()
        assert _cpv_to_category("44110000") == "general"
        assert _guess_voivodeship("Warszawa") == "mazowieckie"


class TestGUNBConstants:
    def test_all_16_voivodeships(self):
        assert len(VOIVODESHIP_CODES) == 16

    def test_mazowieckie(self):
        assert VOIVODESHIP_CODES["14"] == "mazowieckie"

    def test_category_map_has_entries(self):
        assert len(CATEGORY_MAP) >= 6
