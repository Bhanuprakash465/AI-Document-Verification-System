from pathlib import Path
from uuid import uuid4
from datetime import datetime
import re
import shutil
import time

from fastapi import HTTPException, UploadFile

from app.services.image_service import preprocess_image
from app.services.ocr.ocr_service import extract_text
from app.services.document_classifier import classify_document

from app.services.extractor.aadhaar_extractor import (
    extract_aadhaar_fields,
)

from app.services.extractor.driving_license_extractor import (
    extract_driving_license_fields,
)

from app.services.extractor.passport_extractor import (
    extract_passport_fields,
)

from app.services.extractor.voter_id_extractor import (
    extract_voter_id_fields,
)


# =========================================================
# CONFIGURATION
# =========================================================

UPLOAD_FOLDER = (
    Path(__file__).resolve().parents[2]
    / "uploads"
)

MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf",
}


# =========================================================
# REGEX
# =========================================================

PAN_PATTERN = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)


# =========================================================
# HELPERS
# =========================================================

def clean_line(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def clean_name(text: str):

    if not text:
        return None

    text = clean_line(text)

    text = re.sub(
        r"[^A-Za-z.\s'-]",
        " ",
        text,
    )

    text = clean_line(text)

    words = text.split()

    if len(words) < 2:
        return None

    if len(words) > 8:
        return None

    return text.upper()


def parse_date(value: str):

    if not value:
        return None

    value = value.replace(
        ".",
        "/",
    ).replace(
        "-",
        "/",
    )

    for fmt in (
        "%d/%m/%Y",
        "%d/%m/%y",
    ):

        try:

            return datetime.strptime(
                value,
                fmt,
            )

        except ValueError:
            pass

    return None


# =========================================================
# PAN EXTRACTION
# =========================================================

def extract_pan_fields(
    ocr_text: list[str],
) -> dict:

    fields = {

        "document_type": "pan",

        "pan_number": None,

        "name": None,

        "father_name": None,

        "dob": None,
    }

    lines = [

        clean_line(line)

        for line in ocr_text

        if line and line.strip()
    ]

    full_text = "\n".join(lines)

    # ---------------------------------------------------------
    # PAN NUMBER
    # ---------------------------------------------------------

    match = PAN_PATTERN.search(
        full_text
    )

    if match:

        fields["pan_number"] = (
            match.group().upper()
        )

    # ---------------------------------------------------------
    # DOB
    # ---------------------------------------------------------

    for index, line in enumerate(lines):

        if DATE_PATTERN.search(line):

            fields["dob"] = (
                DATE_PATTERN.search(
                    line
                ).group()
            )

            break

    # ---------------------------------------------------------
    # NAME
    # ---------------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "father" in normalized:
            continue

        if not re.search(
            r"\bname\b",
            normalized,
        ):
            continue

        value = re.sub(
            r"(?i).*?\bname\b"
            r"\s*[:\-]?\s*",
            "",
            line,
        ).strip()

        candidate = clean_name(
            value
        )

        if candidate:

            fields["name"] = candidate

            break

        if index + 1 < len(lines):

            candidate = clean_name(
                lines[index + 1]
            )

            if candidate:

                fields["name"] = candidate

                break

    # ---------------------------------------------------------
    # FATHER NAME
    # ---------------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "father" not in normalized:
            continue

        value = re.sub(
            r"(?i).*?father'?s?\s*name"
            r"\s*[:\-]?\s*",
            "",
            line,
        ).strip()

        candidate = clean_name(
            value
        )

        if candidate:

            fields["father_name"] = (
                candidate
            )

            break

        if index + 1 < len(lines):

            candidate = clean_name(
                lines[index + 1]
            )

            if candidate:

                fields["father_name"] = (
                    candidate
                )

                break

    return fields


# =========================================================
# VALIDATION HELPERS
# =========================================================

def base_validation(
    fields: dict,
    document_confidence: float,
) -> dict:

    return {

        "valid": False,

        "errors": [],

        "warnings": [],

        "status": "failed",

        "message": "",

        "confidence": document_confidence,

        "authenticity": "not_verified",

        "checks": {},
    }


def validate_pan(
    fields: dict,
    confidence: float,
) -> dict:

    result = base_validation(
        fields,
        confidence,
    )

    errors = result["errors"]

    checks = result["checks"]

    pan = fields.get(
        "pan_number"
    )

    checks["pan_format"] = bool(
        pan
        and PAN_PATTERN.fullmatch(
            pan.upper()
        )
    )

    if not checks["pan_format"]:

        errors.append(
            "Invalid or missing PAN number."
        )

    checks["name_present"] = bool(
        fields.get("name")
    )

    if not checks["name_present"]:

        errors.append(
            "Name could not be detected."
        )

    checks["dob_present"] = bool(
        fields.get("dob")
    )

    if not checks["dob_present"]:

        errors.append(
            "Date of birth could not be detected."
        )

    result["valid"] = not errors

    result["status"] = (
        "verified"
        if result["valid"]
        else "failed"
    )

    result["message"] = (
        "PAN fields passed structural validation."
        if result["valid"]
        else "PAN requires review."
    )

    return result


def validate_aadhaar_fields(
    fields: dict,
    confidence: float,
) -> dict:

    result = base_validation(
        fields,
        confidence,
    )

    errors = result["errors"]

    checks = result["checks"]

    number = fields.get(
        "aadhaar_number"
    )

    normalized = re.sub(
        r"\D",
        "",
        number or "",
    )

    checks["aadhaar_format"] = (
        len(normalized) == 12
        and normalized.isdigit()
    )

    if not checks["aadhaar_format"]:

        errors.append(
            "Invalid or missing Aadhaar number."
        )

    for field, message in (
        (
            "name",
            "Name could not be detected.",
        ),
        (
            "dob",
            "Date of birth could not be detected.",
        ),
        (
            "gender",
            "Gender could not be detected.",
        ),
    ):

        checks[
            f"{field}_present"
        ] = bool(
            fields.get(field)
        )

        if not fields.get(field):

            errors.append(message)

    pin = fields.get(
        "pin_code"
    )

    if pin:

        checks["pin_format"] = bool(
            re.fullmatch(
                r"[1-9][0-9]{5}",
                pin,
            )
        )

        if not checks["pin_format"]:

            errors.append(
                "Invalid PIN code."
            )

    result["valid"] = not errors

    result["status"] = (
        "verified"
        if result["valid"]
        else "failed"
    )

    result["message"] = (
        "Aadhaar fields passed structural validation."
        if result["valid"]
        else "Aadhaar requires review."
    )

    return result


def validate_passport(
    fields: dict,
    confidence: float,
) -> dict:

    result = base_validation(
        fields,
        confidence,
    )

    errors = result["errors"]

    warnings = result["warnings"]

    checks = result["checks"]

    passport_number = fields.get(
        "passport_number"
    )

    checks["passport_number_format"] = bool(
        passport_number
        and re.fullmatch(
            r"[A-Z][0-9]{7}",
            passport_number.upper(),
        )
    )

    if not checks[
        "passport_number_format"
    ]:

        errors.append(
            "Passport number could not be validated."
        )

    dob = parse_date(
        fields.get(
            "date_of_birth"
        )
    )

    issue = parse_date(
        fields.get(
            "date_of_issue"
        )
    )

    expiry = parse_date(
        fields.get(
            "date_of_expiry"
        )
    )

    checks["dob_valid"] = (
        dob is not None
    )

    checks["issue_date_valid"] = (
        issue is not None
    )

    checks["expiry_date_valid"] = (
        expiry is not None
    )

    if not dob:

        warnings.append(
            "Date of birth was not detected."
        )

    if not issue:

        warnings.append(
            "Date of issue was not detected."
        )

    if not expiry:

        errors.append(
            "Date of expiry was not detected."
        )

    if issue and expiry:

        checks["date_order_valid"] = (
            issue <= expiry
        )

        if issue > expiry:

            errors.append(
                "Passport issue date is after expiry date."
            )

    if expiry:

        checks["expired"] = (
            expiry < datetime.now()
        )

        if checks["expired"]:

            warnings.append(
                "Passport appears to be expired based on the extracted expiry date."
            )

    if not fields.get("name"):

        warnings.append(
            "Passport name could not be detected."
        )

    result["valid"] = not errors

    result["status"] = (
        "verified"
        if result["valid"]
        else "failed"
    )

    result["message"] = (
        "Passport fields passed structural validation."
        if result["valid"]
        else "Passport requires review."
    )

    return result


def validate_voter_id(
    fields: dict,
    confidence: float,
) -> dict:

    result = base_validation(
        fields,
        confidence,
    )

    errors = result["errors"]

    voter_id = (
        fields.get("voter_id")
        or fields.get("epic_number")
    )

    result["checks"][
        "epic_format"
    ] = bool(
        voter_id
        and re.fullmatch(
            r"[A-Z]{3}[0-9]{7}",
            voter_id.upper(),
        )
    )

    if not result["checks"][
        "epic_format"
    ]:

        errors.append(
            "Invalid or missing Voter ID / EPIC number."
        )

    if not fields.get("name"):

        errors.append(
            "Voter name could not be detected."
        )

    result["valid"] = not errors

    result["status"] = (
        "verified"
        if result["valid"]
        else "failed"
    )

    result["message"] = (
        "Voter ID fields passed structural validation."
        if result["valid"]
        else "Voter ID requires review."
    )

    return result


def validate_driving_license(
    fields: dict,
    confidence: float,
) -> dict:

    result = base_validation(
        fields,
        confidence,
    )

    errors = result["errors"]

    number = (
        fields.get("licence_number")
        or fields.get("license_number")
    )

    if not number:

        errors.append(
            "Driving Licence number could not be detected."
        )

    if not fields.get("name"):

        errors.append(
            "Driving Licence name could not be detected."
        )

    issue = parse_date(
        fields.get("issue_date")
    )

    expiry = parse_date(
        fields.get("expiry_date")
    )

    if issue and expiry:

        result["checks"][
            "date_order_valid"
        ] = issue <= expiry

        if issue > expiry:

            errors.append(
                "Driving Licence issue date is after expiry date."
            )

    if expiry:

        result["checks"]["expired"] = (
            expiry < datetime.now()
        )

        if result["checks"]["expired"]:

            result["warnings"].append(
                "Driving Licence appears to be expired."
            )

    result["valid"] = not errors

    result["status"] = (
        "verified"
        if result["valid"]
        else "failed"
    )

    result["message"] = (
        "Driving Licence fields passed structural validation."
        if result["valid"]
        else "Driving Licence requires review."
    )

    return result


# =========================================================
# MAIN SERVICE
# =========================================================

def verify_document_service(
    file: UploadFile,
):

    # =====================================================
    # FILE VALIDATION
    # =====================================================

    if file.content_type not in ALLOWED_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only JPG, PNG and PDF files are allowed."
            ),
        )

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    # =====================================================
    # SAVE FILE
    # =====================================================

    UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = Path(
        file.filename
    ).name

    file_path = (
        UPLOAD_FOLDER
        / f"{uuid4().hex}_{safe_name}"
    )

    with open(
        file_path,
        "wb",
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer,
        )

    # =====================================================
    # SIZE CHECK
    # =====================================================

    if (
        file_path.stat().st_size
        > MAX_FILE_SIZE
    ):

        file_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=413,
            detail=(
                "The file must be 10 MB or smaller."
            ),
        )

    processed_path = None

    try:

        # =================================================
        # OCR
        # =================================================

        start = time.perf_counter()

        if (
            file.content_type
            == "application/pdf"
        ):

            ocr_text = extract_text(
                str(file_path)
            )

        else:

            processed_path = preprocess_image(
                str(file_path)
            )

            ocr_text = extract_text(
                processed_path
            )

        print(
            "[PERFORMANCE] OCR: "
            f"{time.perf_counter() - start:.2f}s"
        )

        # =================================================
        # CLASSIFICATION
        # =================================================

        full_text = "\n".join(
            ocr_text
        )

        start = time.perf_counter()

        document_info = classify_document(
            full_text
        )

        print(
            "[PERFORMANCE] Classification: "
            f"{time.perf_counter() - start:.2f}s"
        )

        print(
            "[CLASSIFIER RESULT]",
            document_info,
        )

        document_type = document_info.get(
            "document_type",
            "unknown",
        )

        confidence = float(
            document_info.get(
                "confidence",
                0.0,
            )
        )

        # =================================================
        # EXTRACTION
        # =================================================

        fields = {

            "document_type": document_type,

            "name": None,
            "dob": None,
            "date_of_birth": None,

            "gender": None,
            "sex": None,

            "address": None,
            "pin_code": None,

            "aadhaar_number": None,

            "pan_number": None,
            "father_name": None,

            "passport_number": None,
            "surname": None,
            "given_names": None,
            "nationality": None,
            "place_of_birth": None,
            "place_of_issue": None,
            "date_of_issue": None,
            "date_of_expiry": None,

            "voter_id": None,
            "epic_number": None,

            "license_number": None,
            "licence_number": None,
            "issue_date": None,
            "expiry_date": None,
            "blood_group": None,
            "vehicle_classes": [],
        }

        start = time.perf_counter()

        # -------------------------------------------------
        # AADHAAR
        # -------------------------------------------------

        if document_type == "aadhaar":

            extracted = (
                extract_aadhaar_fields(
                    ocr_text
                )
            )

            fields.update(
                extracted
            )

            validation = (
                validate_aadhaar_fields(
                    fields,
                    confidence,
                )
            )

        # -------------------------------------------------
        # PAN
        # -------------------------------------------------

        elif document_type == "pan":

            extracted = (
                extract_pan_fields(
                    ocr_text
                )
            )

            fields.update(
                extracted
            )

            validation = validate_pan(
                fields,
                confidence,
            )

        # -------------------------------------------------
        # PASSPORT
        # -------------------------------------------------

        elif document_type == "passport":

            extracted = extract_passport_fields(
                ocr_text
            )

            fields.update(
                extracted
            )

            # -------------------------------------------------
            # Passport field aliases
            # -------------------------------------------------

            if (
                extracted.get("given_names")
                and not extracted.get("given_name")
            ):
                fields["given_name"] = (
                    extracted["given_names"]
                )

            if (
                extracted.get("date_of_birth")
                and not extracted.get("dob")
            ):
                fields["dob"] = (
                    extracted["date_of_birth"]
                )

            if (
                extracted.get("sex")
                and not extracted.get("gender")
            ):
                fields["gender"] = (
                    extracted["sex"]
                )

            validation = validate_passport(
                fields,
                confidence,
            )

        # -------------------------------------------------
        # VOTER ID
        # -------------------------------------------------

        elif document_type == "voter_id":

            extracted = (
                extract_voter_id_fields(
                    ocr_text
                )
            )

            fields.update(
                extracted
            )

            validation = validate_voter_id(
                fields,
                confidence,
            )

        # -------------------------------------------------
        # DRIVING LICENCE
        # -------------------------------------------------

        elif document_type == "driving_license":

            extracted = (
                extract_driving_license_fields(
                    ocr_text
                )
            )

            fields.update(
                extracted
            )

            # Normalize spelling.

            if (
                extracted.get(
                    "licence_number"
                )
            ):

                fields[
                    "license_number"
                ] = extracted[
                    "licence_number"
                ]

            if (
                extracted.get(
                    "license_number"
                )
            ):

                fields[
                    "licence_number"
                ] = extracted[
                    "license_number"
                ]

            validation = (
                validate_driving_license(
                    fields,
                    confidence,
                )
            )

        # -------------------------------------------------
        # UNKNOWN
        # -------------------------------------------------

        else:

            validation = {

                "valid": False,

                "errors": [
                    "Unsupported document type."
                ],

                "warnings": [],

                "status": "unsupported",

                "message": (
                    "This document type is not "
                    "currently supported."
                ),

                "confidence": confidence,

                "authenticity": "not_verified",

                "checks": {},
            }

        print(
            "[PERFORMANCE] Extraction: "
            f"{time.perf_counter() - start:.2f}s"
        )

        print(
            "[EXTRACTED FIELDS]",
            fields,
        )

        print(
            "[VALIDATION]",
            validation,
        )

        # =================================================
        # FINAL RESPONSE
        # =================================================

        return {

            "filename": safe_name,

            "content_type": file.content_type,

            "saved_to": str(
                file_path
            ),

            "processed_file": (
                str(processed_path)
                if processed_path
                else None
            ),

            "document_type": document_type,

            "document": document_info,

            "ocr_text": ocr_text,

            "fields": fields,

            "validation": validation,

            "message": (
                "Document processed successfully."
            ),
        }

    except HTTPException:

        raise

    except Exception as exc:

        print(
            "[ERROR] Document processing failed:",
            repr(exc),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing failed. "
                "Please try again."
            ),
        ) from exc