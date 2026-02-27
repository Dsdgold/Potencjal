"""Tests for NIP validation."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../apps/api'))

from app.utils.nip import validate_nip, clean_nip, format_nip


def test_valid_nips():
    assert validate_nip("5252344078") is True   # Budimex
    assert validate_nip("7740001454") is True   # PKN Orlen


def test_invalid_nip_checksum():
    assert validate_nip("1234567890") is False
    assert validate_nip("0000000000") is False
    assert validate_nip("5250001009") is False


def test_invalid_nip_format():
    assert validate_nip("123") is False
    assert validate_nip("") is False
    assert validate_nip("abcdefghij") is False
    assert validate_nip("12345678901") is False  # Too long


def test_clean_nip():
    assert clean_nip("525-000-10-09") == "5250001009"
    assert clean_nip("525 000 10 09") == "5250001009"
    assert clean_nip(" 5250001009 ") == "5250001009"


def test_format_nip():
    assert format_nip("5250001009") == "525-000-10-09"
    assert format_nip("123") == "123"  # Too short, return as-is
