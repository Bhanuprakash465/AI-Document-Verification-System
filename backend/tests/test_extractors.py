"""
Unit tests for the document-specific field extractors.

These tests feed SYNTHETIC OCR line lists (as produced by the OCR
stage) into each extractor - no real documents are required. They
verify the regex/heuristic extraction logic in isolation.
"""

import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.services.extractor.aadhaar_extractor import (
    extract_aadhaar_fields,
)
from app.services.extractor.pan_extractor import (
    extract_pan_fields,
)
from app.services.extractor.passport_extractor import (
    extract_passport_fields,
)
from app.services.extractor.driving_license_extractor import (
    extract_driving_license_fields,
)
from app.services.extractor.voter_id_extractor import (
    extract_voter_id_fields,
)


# =========================================================
# AADHAAR
# =========================================================

AADHAAR_LINES = [
    "Government of India",
    "Aadhaar",
    "Unique Identification Authority of India",
    "Name: RAHUL SHARMA",
    "DOB: 14/02/1995",
    "Male",
    "1234 5678 9012",
    "Address: 12-3-456, MG Road",
    "Hyderabad, Telangana 500001",
]


def test_aadhaar_extracts_number():
    fields = extract_aadhaar_fields(AADHAAR_LINES)
    assert fields["aadhaar_number"] == "1234 5678 9012"


def test_aadhaar_extracts_dob():
    fields = extract_aadhaar_fields(AADHAAR_LINES)
    assert fields["dob"] == "14/02/1995"


def test_aadhaar_extracts_gender():
    fields = extract_aadhaar_fields(AADHAAR_LINES)
    assert fields["gender"] == "MALE"


def test_aadhaar_extracts_pin():
    fields = extract_aadhaar_fields(AADHAAR_LINES)
    assert fields["pin_code"] == "500001"


def test_aadhaar_number_with_dashes():
    fields = extract_aadhaar_fields(
        ["Aadhaar Number: 1234-5678-9012"]
    )
    assert fields["aadhaar_number"] == "1234 5678 9012"


def test_aadhaar_empty_input():
    fields = extract_aadhaar_fields([])
    assert fields["aadhaar_number"] is None


# =========================================================
# PAN
# =========================================================

PAN_LINES = [
    "Income Tax Department",
    "Government of India",
    "Permanent Account Number Card",
    "ABCPD1234E",
    "Name: RAHUL SHARMA",
    "Father's Name: SURESH SHARMA",
    "Date of Birth: 14/02/1995",
]


def test_pan_extracts_number():
    fields = extract_pan_fields(PAN_LINES)
    assert fields["pan_number"] == "ABCPD1234E"


def test_pan_extracts_name():
    fields = extract_pan_fields(PAN_LINES)
    assert fields["name"] == "RAHUL SHARMA"


def test_pan_extracts_dob():
    fields = extract_pan_fields(PAN_LINES)
    assert fields["dob"] == "14/02/1995"


def test_pan_lowercase_number_normalized():
    fields = extract_pan_fields(["abcdp1234e"])
    assert fields["pan_number"] == "ABCDP1234E"


# =========================================================
# PASSPORT
# =========================================================

PASSPORT_LINES = [
    "Republic of India",
    "Passport",
    "Type P",
    "Passport No: M1234567",
    "Surname: SHARMA",
    "Given Name: RAHUL",
    "Nationality: INDIAN",
    "Place of Birth: HYDERABAD",
    "Date of Issue: 10/01/2020",
    "Date of Expiry: 09/01/2030",
    "P<INDSHARMA<<RAHUL<<<<<<<<<<<<<<<<<<<<<<",
    "M12345674IND9502142M3001092<<<<<<<<<<<<<<02",
]


def test_passport_extracts_number():
    fields = extract_passport_fields(PASSPORT_LINES)
    assert fields["passport_number"] == "M1234567"


def test_passport_extracts_surname():
    fields = extract_passport_fields(PASSPORT_LINES)
    assert fields["surname"] == "SHARMA"


def test_passport_extracts_expiry():
    fields = extract_passport_fields(PASSPORT_LINES)
    assert fields["date_of_expiry"] == "09/01/2030"


# =========================================================
# DRIVING LICENCE
# =========================================================

DL_LINES = [
    "Transport Department",
    "Government of Telangana",
    "Driving Licence",
    "DL NO: TS0120190001234",
    "Name: RAHUL SHARMA",
    "Date of Birth: 14/02/1995",
    "Blood Group: B+",
    "Valid From: 01/06/2019",
    "Valid Upto: 31/05/2039",
]


def test_dl_extracts_number():
    fields = extract_driving_license_fields(DL_LINES)
    number = (
        fields.get("license_number")
        or fields.get("licence_number")
    )
    assert number


def test_dl_extracts_name():
    fields = extract_driving_license_fields(DL_LINES)
    assert fields.get("name")


def test_dl_ocr_variant_label():
    # "DL NO" is often misread as "DLI NO" and T as 1.
    fields = extract_driving_license_fields(
        ["DLI NO: 1S0120190001234"]
    )
    assert fields["licence_number"] == "1S0120190001234"


def test_dl_number_not_swallowed_from_next_line():
    # Regression: a whole-text search matched "LICENCE" at the end
    # of the heading line and captured "DLI NO" from the next line.
    fields = extract_driving_license_fields(
        [
            "DRIVING LICENCE",
            "DLI NO: 1S0120190001234",
        ]
    )
    assert fields["licence_number"] == "1S0120190001234"


def test_dl_number_spaces_stripped():
    fields = extract_driving_license_fields(
        ["Licence No: MH12 20110001234"]
    )
    assert fields["licence_number"] == "MH1220110001234"


DL_ISSUE_EXPIRY_CASES = [
    # Reported production case: DOI + "Valid Till ... (NT)".
    (
        ["Driving Licence", "DOI: 24-01-2007", "Valid Till 23-01-2027 (NT)"],
        ("24-01-2007", "23-01-2027"),
    ),
    (
        ["Driving Licence", "DATE OF ISSUE 24.01.2007", "VALID UNTIL 23.01.2027"],
        ("24.01.2007", "23.01.2027"),
    ),
    (
        ["Driving Licence", "ISSUED ON 24/01/2007", "VALID UPTO 23/01/2027"],
        ("24/01/2007", "23/01/2027"),
    ),
    (
        ["Driving Licence", "ISSUE DATE: 24-01-2007", "VALID TO: 23-01-2027"],
        ("24-01-2007", "23-01-2027"),
    ),
    (
        ["Driving Licence", "VALID FROM 24-01-2007", "VALIDITY 23-01-2027"],
        ("24-01-2007", "23-01-2027"),
    ),
    (
        ["Driving Licence", "D0I: 24-01-2007", "VALID T1LL 23-01-2027"],
        ("24-01-2007", "23-01-2027"),
    ),
]


def test_dl_issue_expiry_label_variants():
    for lines, (issue, expiry) in DL_ISSUE_EXPIRY_CASES:
        fields = extract_driving_license_fields(lines)
        assert fields["issue_date"] == issue, lines
        assert fields["expiry_date"] == expiry, lines


def test_dl_place_of_issue_is_not_issue_date():
    # "PLACE OF ISSUE: NEW DELHI" carries no date and must not populate
    # issue_date.
    fields = extract_driving_license_fields(
        ["Driving Licence", "PLACE OF ISSUE: NEW DELHI"]
    )
    assert fields["issue_date"] is None
    assert fields["expiry_date"] is None


# =========================================================
# VOTER ID
# =========================================================

VOTER_LINES = [
    "Election Commission of India",
    "Elector's Photo Identity Card",
    "EPIC Number: ABC1234567",
    "Name: RAHUL SHARMA",
    "Father's Name: SURESH SHARMA",
    "Date of Birth: 14/02/1995",
]


def test_voter_extracts_epic():
    fields = extract_voter_id_fields(VOTER_LINES)
    epic = (
        fields.get("voter_id")
        or fields.get("epic_number")
    )
    assert epic == "ABC1234567"


def test_voter_extracts_name():
    fields = extract_voter_id_fields(VOTER_LINES)
    assert fields.get("name") == "RAHUL SHARMA"


def test_voter_multiline_name_continues():
    # Surname wrapped onto the next line is merged.
    fields = extract_voter_id_fields(
        [
            "Election Commission of India",
            "Name: RAHUL",
            "SHARMA",
            "ABC1234567",
        ]
    )
    assert fields.get("name") == "RAHUL SHARMA"


def test_voter_name_does_not_swallow_epic():
    # An identifier-looking next line must NOT be appended to the name.
    fields = extract_voter_id_fields(
        [
            "Election Commission of India",
            "Name: RAHUL SHARMA",
            "ABC1234567",
        ]
    )
    assert fields.get("name") == "RAHUL SHARMA"


def test_voter_name_does_not_swallow_garbage():
    fields = extract_voter_id_fields(
        [
            "Election Commission of India",
            "Name: RAHUL SHARMA",
            "RANDOM GARBAGE 123",
            "ABC1234567",
        ]
    )
    assert fields.get("name") == "RAHUL SHARMA"


# =========================================================
# REAL-WORLD OCR REGRESSION (reported production failures)
# =========================================================

# Real Aadhaar photo: Devanagari-derived OCR garbage lines must
# lose to the real person name, and "Name:" labels must not leak
# into the extracted name.
REPORTED_AADHAAR_LINES = [
    "M R",
    "GOVERNMENT OFINDIA",
    "SSSTRT IT",
    "Prakash Ranjan",
    "sp fafl DOB: 05/07/1994",
    "354 IMALE",
    "9183 0074 6619",
    "STETK-3T4 3TCT T3fE4R",
    "Scanned by CamScanner",
]


def test_aadhaar_name_ignores_ocr_garbage():
    fields = extract_aadhaar_fields(REPORTED_AADHAAR_LINES)
    assert fields["name"] == "PRAKASH RANJAN"
    assert fields["dob"] == "05/07/1994"
    assert fields["gender"] == "MALE"
    assert fields["aadhaar_number"] == "9183 0074 6619"


def test_aadhaar_name_label_not_included():
    fields = extract_aadhaar_fields(
        [
            "Government of India",
            "Aadhaar",
            "Name: RAHUL SHARMA",
            "DOB: 14/02/1995",
            "Male",
            "1234 5678 9012",
        ]
    )
    assert fields["name"] == "RAHUL SHARMA"


# Real passport photo: OCR linearised the issue/expiry area so
# BOTH dates appeared after the "Date of Expiry" label, and the
# MRZ line 1 was malformed (P<<SPECIMEN...).
REPORTED_PASSPORT_LINES = [
    "EC URISATF REPUBLIC OF INDIA",
    "aType",
    "a3Code",
    "RT Nationality",
    "SEREIPAssport No,",
    "IND",
    "RRGR / INDIAN",
    "20000000",
    "34/Sumname",
    "SPECIMEN",
    "Rain /Given Namels)",
    "KUMAR G",
    "ae/ Date of Birth",
    "T/Sex",
    "24/05/1985",
    "ut u/Place of Birth",
    "MUMBAI, MAHARASHTRA",
    "GIe BT R1 Place of issue",
    "BANGALORE",
    "MaR a fr Date of Issue",
    "aT",
    "N.Woeses",
    "#RT f/Date of Expiry",
    "01/01/2013",
    "01/01/2023",
    "P<<SPECIMENKKKUMARKGKKK<<<KKK<<<<K<<K<<",
    "Z9999999<0IND8505246M2300000<<K<K<<<<<4",
]


def test_passport_issue_and_expiry_dates_distinguished():
    fields = extract_passport_fields(REPORTED_PASSPORT_LINES)
    assert fields["date_of_issue"] == "01/01/2013"
    assert fields["date_of_expiry"] == "01/01/2023"


def test_passport_names_from_visual_ocr_not_malformed_mrz():
    # The malformed MRZ (P<<SPECIMEN...) must NOT be parsed into
    # concatenated name fields; the visual OCR values win.
    fields = extract_passport_fields(REPORTED_PASSPORT_LINES)
    assert fields["surname"] == "SPECIMEN"
    assert fields["given_names"] == "KUMAR G"
    assert fields["name"] == "KUMAR G SPECIMEN"


def test_passport_clean_mrz_still_parses():
    fields = extract_passport_fields(
        [
            "P<INDSHARMA<<RAHUL<<<<<<<<<<<<<<<<<<<<<<",
            "M1234567<4IND9502142M3001092<<<<<<<<<<<<<<02",
        ]
    )
    assert fields["surname"] == "SHARMA"
    assert fields["given_names"] == "RAHUL"
    assert fields["passport_number"] == "M1234567"
    assert fields["date_of_birth"] == "14/02/1995"
    assert fields["date_of_expiry"] == "09/01/2030"
    assert fields["sex"] == "MALE"
