"""
Unit tests for the validation logic in document_service.

These tests call the per-document-type validators directly with
synthetic field dicts - no real documents are required.
"""

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.services.document_service import (
    validate_aadhaar_fields,
    validate_pan,
    validate_passport,
    validate_voter_id,
    validate_driving_license,
    parse_date,
    clean_name,
)


# =========================================================
# AADHAAR VALIDATION
# =========================================================

def test_aadhaar_valid():
    result = validate_aadhaar_fields(
        {
            "aadhaar_number": "1234 5678 9012",
            "name": "RAHUL SHARMA",
            "dob": "14/02/1995",
            "gender": "MALE",
            "pin_code": "500001",
        },
        0.9,
    )
    assert result["valid"] is True
    assert result["status"] == "verified"
    assert result["errors"] == []


def test_aadhaar_missing_number():
    result = validate_aadhaar_fields(
        {
            "aadhaar_number": None,
            "name": "RAHUL SHARMA",
            "dob": "14/02/1995",
            "gender": "MALE",
        },
        0.9,
    )
    assert result["valid"] is False
    assert any("Aadhaar number" in e for e in result["errors"])


def test_aadhaar_bad_pin():
    result = validate_aadhaar_fields(
        {
            "aadhaar_number": "1234 5678 9012",
            "name": "RAHUL SHARMA",
            "dob": "14/02/1995",
            "gender": "MALE",
            "pin_code": "050001",
        },
        0.9,
    )
    assert result["valid"] is False
    assert any("PIN" in e for e in result["errors"])


# =========================================================
# PAN VALIDATION
# =========================================================

def test_pan_valid():
    result = validate_pan(
        {
            "pan_number": "ABCPD1234E",
            "name": "RAHUL SHARMA",
            "dob": "14/02/1995",
        },
        0.9,
    )
    assert result["valid"] is True
    assert result["status"] == "verified"


def test_pan_invalid_format():
    result = validate_pan(
        {
            "pan_number": "12345",
            "name": "RAHUL SHARMA",
            "dob": "14/02/1995",
        },
        0.9,
    )
    assert result["valid"] is False


# =========================================================
# PASSPORT VALIDATION
# =========================================================

def test_passport_valid():
    result = validate_passport(
        {
            "passport_number": "M1234567",
            "date_of_issue": "10/01/2020",
            "date_of_expiry": "09/01/2030",
            "name": "RAHUL SHARMA",
        },
        0.9,
    )
    assert result["valid"] is True
    assert result["status"] == "verified"


def test_passport_expired_warns():
    result = validate_passport(
        {
            "passport_number": "M1234567",
            "date_of_issue": "10/01/2015",
            "date_of_expiry": "09/01/2020",
        },
        0.9,
    )
    assert result["valid"] is True  # expiry is a warning, not error
    assert any("expired" in w.lower() for w in result["warnings"])


def test_passport_issue_after_expiry():
    result = validate_passport(
        {
            "passport_number": "M1234567",
            "date_of_issue": "10/01/2031",
            "date_of_expiry": "09/01/2030",
        },
        0.9,
    )
    assert result["valid"] is False


def test_passport_missing_expiry():
    result = validate_passport(
        {
            "passport_number": "M1234567",
        },
        0.9,
    )
    assert result["valid"] is False


# =========================================================
# VOTER ID VALIDATION
# =========================================================

def test_voter_valid():
    result = validate_voter_id(
        {
            "voter_id": "ABC1234567",
            "name": "RAHUL SHARMA",
        },
        0.9,
    )
    assert result["valid"] is True


def test_voter_invalid_epic():
    result = validate_voter_id(
        {
            "voter_id": "12AB",
            "name": "RAHUL SHARMA",
        },
        0.9,
    )
    assert result["valid"] is False


# =========================================================
# DRIVING LICENCE VALIDATION
# =========================================================

def test_dl_valid():
    result = validate_driving_license(
        {
            "license_number": "TS0120190001234",
            "name": "RAHUL SHARMA",
            "issue_date": "01/06/2019",
            "expiry_date": "31/05/2039",
        },
        0.9,
    )
    assert result["valid"] is True


def test_dl_missing_number():
    result = validate_driving_license(
        {
            "name": "RAHUL SHARMA",
        },
        0.9,
    )
    assert result["valid"] is False


# =========================================================
# HELPERS
# =========================================================

def test_parse_date_slashes():
    assert parse_date("14/02/1995") is not None


def test_parse_date_dashes():
    assert parse_date("14-02-1995") is not None


def test_parse_date_invalid():
    assert parse_date("31/02/1995") is None
    assert parse_date("garbage") is None


def test_clean_name_rejects_single_word():
    assert clean_name("RAHUL") is None


def test_clean_name_accepts_two_words():
    assert clean_name("RAHUL SHARMA") == "RAHUL SHARMA"