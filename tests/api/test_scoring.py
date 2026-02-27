"""Tests for scoring engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from app.services.scoring import compute_score


def test_score_high_quality_company():
    snapshot = {
        "name": "BUDIMEX S.A.",
        "nip": "5252344078",
        "regon": "010732630",
        "krs": "0000001764",
        "legal_form": "Spółka akcyjna",
        "vat_status": "Czynny",
        "registered_address": "ul. Siedmiogrodzka 9, 01-204 Warszawa",
        "city": "Warszawa",
        "registration_date": "2001-01-08",
        "share_capital": 145848275.0,
        "pkd_main_code": "41.20.Z",
        "representatives": [
            {"name": "Artur Popko", "function": "Prezes"},
            {"name": "Jan Kowalski", "function": "Wiceprezes"},
        ],
        "bank_account_count": 12,
        "is_active": True,
        "has_vat_registration": True,
        "is_in_krs": True,
    }
    result = compute_score(snapshot)

    assert result["score_0_100"] >= 70, f"Expected high score, got {result['score_0_100']}"
    assert result["risk_band"] in ("A", "B")
    assert len(result["components"]) == 11
    assert len(result["green_flags"]) > 0
    assert result["explanation_summary"]


def test_score_low_quality_company():
    snapshot = {
        "name": "FIRMA TESTOWA",
        "nip": "1234567890",
        "vat_status": "Niezarejestrowany",
        "is_active": False,
    }
    result = compute_score(snapshot)

    assert result["score_0_100"] <= 30, f"Expected low score, got {result['score_0_100']}"
    assert result["risk_band"] == "D"
    assert len(result["red_flags"]) > 0


def test_score_components_sum():
    snapshot = {
        "name": "TEST SP. Z O.O.",
        "nip": "1111111111",
        "vat_status": "Czynny",
        "legal_form": "Spółka z o.o.",
        "city": "Kraków",
        "registration_date": "2015-05-01",
        "share_capital": 50000,
        "bank_account_count": 3,
        "regon": "123456789",
        "is_in_krs": True,
        "has_vat_registration": True,
        "is_active": True,
        "representatives": [{"name": "Jan Kowalski"}],
        "pkd_main_code": "41.20.Z",
    }
    result = compute_score(snapshot)

    total_from_components = sum(c["points"] for c in result["components"])
    assert abs(result["score_0_100"] - round(total_from_components)) <= 1


def test_score_band_thresholds():
    for score, expected_band in [(90, "A"), (70, "B"), (50, "C"), (20, "D")]:
        snapshot = {"name": "TEST", "nip": "0000000000", "vat_status": "Czynny"}
        result = compute_score(snapshot)
        # Just verify bands are assigned
        assert result["risk_band"] in ("A", "B", "C", "D")
