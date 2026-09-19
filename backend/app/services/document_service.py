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
from app.database.database import SessionLocal
from app.models.document import Document

from app.services.extractor.aadhaar_extractor import (
    extract_aadhaar_fields,
)

from app.services.extractor.pan_extractor import (
    extract_pan_fields,
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

# Content-Type values browsers/clients commonly send for each
# supported format. Kept broad on purpose - different browsers and
# operating systems are inconsistent about MIME types for BMP/TIFF.
ALLOWED_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "image/x-ms-bmp",
    "image/x-bmp",
    "image/tiff",
    "image/tif",
    "application/pdf",
}

# Fallback check by file extension. Content-Type alone is not
# trustworthy (some browsers send "application/octet-stream" for
# BMP/TIFF), and extension alone is not trustworthy either (it can
# be forged) - so a file is accepted if EITHER signal matches, and
# the real gatekeeper is that the file must then actually decode
# successfully as an image or PDF later in this pipeline.
ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff",
    ".tif",
    ".pdf",
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


def _relative_to_backend(path) -> str | None:
    """
    Convert an absolute server-side path into a path relative to the
    backend directory. Absolute local filesystem paths must not leak
    into public API responses.
    """

    if not path:
        return None

    try:
        return str(
            Path(path).resolve().relative_to(
                Path(__file__).resolve().parents[2]
            )
        )
    except ValueError:
        # Outside the backend tree - return only the file name.
        return Path(path).name


def persist_document(
    filename: str,
    document_type: str,
    ocr_text: list[str],
    verification_status: str,
) -> None:
    """
    Persist a verification result to the database.

    Persistence is a best-effort side effect: a database problem
    must NEVER break the verification response, so every error is
    caught and logged only.
    """

    db = None

    try:

        db = SessionLocal()

        record = Document(
            filename=filename,
            document_type=document_type,
            extracted_text="\n".join(ocr_text or [])[:200000],
            verification_status=verification_status,
        )

        db.add(record)
        db.commit()

    except Exception as exc:  # pragma: no cover - defensive

        print(
            "[DB] Failed to persist document record:",
            repr(exc),
        )

        if db is not None:
            db.rollback()

    finally:

        if db is not None:
            db.close()


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

    # -----------------------------------------------------
    # MRZ vs visual-OCR date conflicts detected by the
    # extractor are surfaced as warnings, never silently
    # resolved.
    # -----------------------------------------------------

    for conflict in fields.get("date_warnings") or []:
        warnings.append(str(conflict))

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

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    # Use only the final path component - this also prevents
    # path traversal via a crafted filename (e.g. "../../evil").
    safe_name = Path(
        file.filename
    ).name

    extension = Path(safe_name).suffix.lower()

    type_is_allowed = (
        file.content_type in ALLOWED_TYPES
    )

    extension_is_allowed = (
        extension in ALLOWED_EXTENSIONS
    )

    if not type_is_allowed and not extension_is_allowed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. Please upload a JPG, "
                "JPEG, PNG, WEBP, BMP, TIFF or PDF file."
            ),
        )

    # A PDF is routed to the PDF-specific OCR path if EITHER the
    # content type or the extension says so, since real-world
    # clients are inconsistent about which one they set correctly.
    is_pdf = (
        extension == ".pdf"
        or file.content_type == "application/pdf"
    )

    # =====================================================
    # SAVE FILE
    # =====================================================

    UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )

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

        if is_pdf:

            ocr_text = extract_text(
                str(file_path)
            )

        else:

            processed_path = preprocess_image(
                str(file_path),
                mode="enhanced",
            )

            ocr_text = extract_text(
                processed_path
            )

            # -------------------------------------------------
            # CONTROLLED FALLBACK
            # -------------------------------------------------
            # If the enhanced pipeline (grayscale + contrast +
            # sharpening) found nothing, try again with a lighter
            # "minimal" preprocessing pass before giving up. This
            # is a single, deterministic extra attempt - not an
            # open-ended retry loop - so it stays fast.
            # -------------------------------------------------

            if not ocr_text:

                print(
                    "[OCR] Enhanced pass found no text - "
                    "retrying with minimal preprocessing."
                )

                fallback_path = preprocess_image(
                    str(file_path),
                    mode="minimal",
                )

                fallback_text = extract_text(
                    fallback_path
                )

                if fallback_text:

                    ocr_text = fallback_text
                    processed_path = fallback_path

        print(
            "[PERFORMANCE] OCR: "
            f"{time.perf_counter() - start:.2f}s"
        )

        # =================================================
        # OCR FAILURE CHECK
        # =================================================
        # If OCR extracted zero usable text after every attempt,
        # this is NOT a verified (or even "unsupported type")
        # result - it is an OCR failure, and must be reported as
        # such rather than silently continuing.
        # =================================================

        if not ocr_text:

            print(
                "[OCR] No text detected after all attempts."
            )

            validation = {

                "valid": False,

                "errors": [
                    "No readable text could be extracted "
                    "from this document."
                ],

                "warnings": [],

                "status": "ocr_failed",

                "message": (
                    "OCR could not detect any text in the "
                    "uploaded document. Please upload a "
                    "clearer, well-lit photo or a higher "
                    "resolution scan."
                ),

                "confidence": 0.0,

                "authenticity": "not_verified",

                "checks": {},
            }

            return {

                "filename": safe_name,

                "content_type": file.content_type,

                "saved_to": _relative_to_backend(
                    file_path
                ),

                "processed_file": (
                    _relative_to_backend(
                        processed_path
                    )
                ),

                "document_type": "unknown",

                "display_name": "Unknown Document",

                "confidence": 0.0,

                "document": {
                    "document_type": "unknown",
                    "display_name": "Unknown Document",
                    "confidence": 0.0,
                },

                "ocr_text": [],

                "fields": {
                    "document_type": "unknown",
                },

                "validation": validation,

                "message": (
                    "OCR failed: no text detected."
                ),
            }

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

        if validation.get("valid"):
            top_level_message = (
                "Document processed and verified successfully."
            )
        elif validation.get("status") == "unsupported":
            top_level_message = (
                "Document processed, but this document type "
                "is not currently supported."
            )
        else:
            top_level_message = (
                "Document processed, but verification failed "
                "or requires review."
            )

        # =================================================
        # PERSISTENCE (best-effort, never breaks the response)
        # =================================================

        persist_document(

            filename=safe_name,

            document_type=document_type,

            ocr_text=ocr_text,

            verification_status=(
                validation.get("status")
                or (
                    "verified"
                    if validation.get("valid")
                    else "failed"
                )
            ),
        )

        return {

            "filename": safe_name,

            "content_type": file.content_type,

            "saved_to": _relative_to_backend(
                file_path
            ),

            "processed_file": (
                _relative_to_backend(
                    processed_path
                )
            ),

            "document_type": document_type,

            "display_name": document_info.get(
                "display_name"
            ),

            "confidence": confidence,

            "document": document_info,

            "ocr_text": ocr_text,

            "fields": fields,

            "validation": validation,

            "message": top_level_message,
        }

    except HTTPException:

        raise

    except ValueError as exc:

        # Raised deliberately by image_service.py for user-facing
        # problems with the uploaded file itself (corrupt file,
        # undecodable image, degenerate/too-small crop, etc). The
        # message is already safe to show to the user - no stack
        # trace or internal details are included.

        print(
            "[ERROR] Invalid document:",
            repr(exc),
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

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