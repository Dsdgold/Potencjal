"""Tests for credit limit engine."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from app.services.credit import compute_credit_limit


def test_band_a_high_limit():
    result = compute_credit_limit(85, "A", {
        "registration_date": "2005-01-01",
        "share_capital": 5000000,
        "bank_account_count": 25,
        "is_active": True,
    }, [])
    assert result["credit_limit_suggested"] > 0
    assert result["payment_terms_days"] == 60
    assert result["discount_pct"] == 15.0


def test_band_d_prepayment():
    result = compute_credit_limit(20, "D", {"is_active": True}, [])
    assert result["credit_limit_suggested"] == 0
    assert result["payment_terms_days"] == 0


def test_inactive_company_zero():
    result = compute_credit_limit(80, "A", {"is_active": False}, [])
    assert result["credit_limit_suggested"] == 0
    assert "nieaktywna" in result["explanation"].lower()


def test_young_company_reduction():
    result_young = compute_credit_limit(60, "B", {
        "registration_date": "2025-01-01",
        "is_active": True,
    }, [])
    result_old = compute_credit_limit(60, "B", {
        "registration_date": "2005-01-01",
        "is_active": True,
    }, [])
    assert result_young["credit_limit_suggested"] <= result_old["credit_limit_suggested"]
