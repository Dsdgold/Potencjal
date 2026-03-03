"""Tests for Pydantic schemas — validation, serialization."""

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.leads.schemas import LeadCreate, LeadOut, LeadUpdate, LeadActionCreate


class TestLeadCreate:
    def test_minimal_valid(self):
        lead = LeadCreate(name="Test Company")
        assert lead.name == "Test Company"
        assert lead.source == "manual"

    def test_full_valid(self):
        lead = LeadCreate(
            name="Firma Budowlana",
            nip="1234567890",
            city="Warszawa",
            employees=50,
            revenue_pln=5_000_000,
            source="bzp",
            category="cement_concrete",
            cpv_codes=["44100000"],
        )
        assert lead.nip == "1234567890"
        assert lead.category == "cement_concrete"
        assert lead.cpv_codes == ["44100000"]

    def test_invalid_nip_format(self):
        with pytest.raises(ValidationError):
            LeadCreate(name="Test", nip="abc")

    def test_invalid_nip_length(self):
        with pytest.raises(ValidationError):
            LeadCreate(name="Test", nip="12345")  # too short

    def test_negative_employees_rejected(self):
        with pytest.raises(ValidationError):
            LeadCreate(name="Test", employees=-1)

    def test_negative_revenue_rejected(self):
        with pytest.raises(ValidationError):
            LeadCreate(name="Test", revenue_pln=-100)

    def test_missing_name_rejected(self):
        with pytest.raises(ValidationError):
            LeadCreate()  # name is required


class TestLeadUpdate:
    def test_partial_update(self):
        update = LeadUpdate(city="Kraków")
        assert update.city == "Kraków"
        assert update.name is None

    def test_empty_update(self):
        update = LeadUpdate()
        assert update.name is None
        assert update.city is None


class TestLeadActionCreate:
    def test_valid_action(self):
        action = LeadActionCreate(action="contacted", note="Zadzwoniłem")
        assert action.action == "contacted"

    def test_action_without_note(self):
        action = LeadActionCreate(action="viewed")
        assert action.note is None
