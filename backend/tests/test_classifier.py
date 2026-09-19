"""
Unit tests for the document classifier.

These tests use SYNTHETIC OCR text (plain strings) - no real
documents are required. They verify the weighted keyword /
identifier / MRZ scoring logic in isolation.
"""

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.services.document_classifier import classify_document


AADHAAR_TEXT = """
Government of India
Aadhaar
Unique Identification Authority of India
Name: RAHUL SHARMA
DOB: 14/02/1995
Male
1234 5678 9012
Address: 12-3-456, MG Road
Hyderabad, Telangana 500001
"""

PAN_TEXT = """
Income Tax Department
Government of India
Permanent Account Number Card
PAN
ABCPD1234E
Name: RAHUL SHARMA
Father's Name: SURESH SHARMA
Date of Birth: 14/02/1995
"""

PASSPORT_TEXT = """
Republic of India
Passport
Type P
Passport No: M1234567
Surname: SHARMA
Given Name: RAHUL
Nationality: INDIAN
Place of Birth: HYDERABAD
Date of Issue: 10/01/2020
Date of Expiry: 09/01/2030
P<INDSHARMA<<RAHUL<<<<<<<<<<<<<<<<<<<<<<
M12345674IND9502142M3001092<<<<<<<<<<<<<<02
"""

DL_TEXT = """
Transport Department
Government of Telangana
Driving Licence
DRIVING LICENCE NO: TS0120190001234
Name: RAHUL SHARMA
S/O SURESH SHARMA
Date of Birth: 14/02/1995
Blood Group: B+
Valid From: 01/06/2019
Valid Upto: 31/05/2039
Vehicle Class: LMV, MCWG
"""

VOTER_TEXT = """
Election Commission of India
Elector's Photo Identity Card
EPIC Number: ABC1234567
Name: RAHUL SHARMA
Father's Name: SURESH SHARMA
Date of Birth: 14/02/1995
Gender: Male
"""

UNKNOWN_TEXT = """
Grocery Store Receipt
Milk 2.50
Bread 1.80
Total 4.30
Thank you for shopping
"""


def test_classifies_aadhaar():
    result = classify_document(AADHAAR_TEXT)
    assert result["document_type"] == "aadhaar"
    assert result["confidence"] >= 0.5


def test_classifies_pan():
    result = classify_document(PAN_TEXT)
    assert result["document_type"] == "pan"
    assert result["confidence"] >= 0.5


def test_classifies_passport():
    result = classify_document(PASSPORT_TEXT)
    assert result["document_type"] == "passport"
    assert result["confidence"] >= 0.5


def test_classifies_driving_license():
    result = classify_document(DL_TEXT)
    assert result["document_type"] == "driving_license"


def test_classifies_voter_id():
    result = classify_document(VOTER_TEXT)
    assert result["document_type"] == "voter_id"


def test_unknown_document():
    result = classify_document(UNKNOWN_TEXT)
    assert result["document_type"] == "unknown"


def test_empty_text():
    result = classify_document("")
    assert result["document_type"] == "unknown"
    assert result["confidence"] == 0.0


def test_lone_aadhaar_number_is_not_enough():
    # A bare 12-digit number must NOT classify as Aadhaar.
    result = classify_document("1234 5678 9012")
    assert result["document_type"] == "unknown"


def test_classifier_accepts_list_input():
    result = classify_document(
        [
            "Income Tax Department",
            "Permanent Account Number Card",
            "ABCPD1234E",
        ]
    )
    assert result["document_type"] == "pan"


# =========================================================
# REAL-WORLD OCR REGRESSION (reported production failure)
# =========================================================
# A real Aadhaar photo produced this OCR text and was classified
# as "unknown" because "GOVERNMENT OFINDIA" (missing space) did
# not match the keyword pattern and the 12-digit number alone
# was deliberately not enough evidence.
# =========================================================

REPORTED_AADHAAR_OCR = """GOVERNMENT OFINDIA
Prakash Ranjan
DOB: 05/07/1994
9183 0074 6619"""


def test_reported_real_aadhaar_ocr_is_classified():
    result = classify_document(REPORTED_AADHAAR_OCR)
    assert result["document_type"] == "aadhaar"
    assert result["confidence"] >= 0.5
    # Signals must explain WHY.
    assert result["signals"]
    assert result["scores"]["aadhaar"] > 0


def test_fused_keywords_still_match():
    # OCR fuses words: "INCOMETAXDEPARTMENT", "PERMANENTACCOUNTNUMBER".
    result = classify_document(
        "INCOMETAXDEPARTMENT PERMANENTACCOUNTNUMBER HFTPB6963J"
    )
    assert result["document_type"] == "pan"


def test_aadhaar_alternate_spellings():
    for spelling in ("Aadhaar", "Aadhar", "Adhaar", "Adhar"):
        result = classify_document(
            f"{spelling} Card Unique Identification 9183 0074 6619"
        )
        assert result["document_type"] == "aadhaar", spelling


def test_name_and_dob_alone_is_not_aadhaar():
    # DOB label alone (1.5) is below MIN_SCORE - no identifier,
    # no strong keyword -> must stay unknown.
    result = classify_document("Prakash Ranjan DOB: 05/07/1994")
    assert result["document_type"] == "unknown"


def test_lone_pan_string_is_not_enough():
    result = classify_document("HFTPB6963J")
    assert result["document_type"] == "unknown"
