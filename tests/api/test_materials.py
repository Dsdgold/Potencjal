"""Tests for material recommendation engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from app.services.materials import recommend_materials


def test_construction_company_gets_recommendations():
    snapshot = {
        "name": "BUDIMEX S.A.",
        "pkd_main_code": "41.20.Z",
        "pkd_main_name": "Roboty budowlane związane ze wznoszeniem budynków",
        "pkd_codes": [
            {"code": "41.20.Z", "name": "Roboty budowlane", "main": True},
            {"code": "42.11.Z", "name": "Roboty drogowe", "main": False},
        ],
    }
    result = recommend_materials(snapshot)

    assert len(result["categories"]) > 0
    codes = [c["code"] for c in result["categories"]]
    assert "cement" in codes
    assert "rebar" in codes
    assert result["explanation"]


def test_non_construction_company():
    snapshot = {
        "name": "FIRMA IT SP. Z O.O.",
        "pkd_main_code": "62.01.Z",
        "pkd_codes": [{"code": "62.01.Z", "name": "Działalność IT", "main": True}],
    }
    result = recommend_materials(snapshot)

    # Should return fewer or no recommendations
    high_confidence = [c for c in result["categories"] if c["confidence"] >= 0.5]
    assert len(high_confidence) == 0


def test_keyword_matching():
    snapshot = {
        "name": "PRODUCENT CEMENTU I BETONU SP. Z O.O.",
        "pkd_main_code": "23.51.Z",
        "pkd_codes": [{"code": "23.51.Z", "name": "Produkcja cementu", "main": True}],
    }
    result = recommend_materials(snapshot)
    codes = [c["code"] for c in result["categories"]]
    assert "cement" in codes


def test_confidence_range():
    snapshot = {
        "pkd_main_code": "41.20.Z",
        "pkd_codes": [{"code": "41.20.Z", "name": "Budownictwo", "main": True}],
    }
    result = recommend_materials(snapshot)
    for cat in result["categories"]:
        assert 0 <= cat["confidence"] <= 1.0
