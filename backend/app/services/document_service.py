from pathlib import Path
from uuid import uuid4
import re
import shutil
import time

from fastapi import HTTPException, UploadFile

from app.services.image_service import preprocess_image
from app.services.ocr.ocr_service import extract_text
from app.services.extractor import extract_fields
from app.services.validator import validate_aadhaar
from app.services.document_classifier import classify_document


UPLOAD_FOLDER = (
    Path(__file__).resolve().parents[2] / "uploads"
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

DOB_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)


# =========================================================
# COMMON HELPERS
# =========================================================

def clean_line(text: str) -> str:

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def clean_name(text: str):

    if not text:
        return None

    text = clean_line(text)

    # Remove common OCR punctuation.
    text = re.sub(
        r"[^A-Za-z.\s]",
        " ",
        text,
    )

    text = clean_line(text)

    if not text:
        return None

    words = text.split()

    if len(words) < 2:
        return None

    if len(words) > 8:
        return None

    return text.upper()


# =========================================================
# PAN EXTRACTION
# =========================================================

def extract_pan_fields(
    ocr_text: list[str],
) -> dict:

    fields = {
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

    # -----------------------------------------------------
    # PAN NUMBER
    # -----------------------------------------------------

    full_text = "\n".join(lines)

    pan_match = PAN_PATTERN.search(
        full_text
    )

    if pan_match:

        fields["pan_number"] = (
            pan_match.group().upper()
        )


    # -----------------------------------------------------
    # DATE OF BIRTH
    # -----------------------------------------------------

    for line in lines:

        dob_match = DOB_PATTERN.search(
            line
        )

        if dob_match:

            fields["dob"] = (
                dob_match.group()
            )

            break


    # -----------------------------------------------------
    # FIND NAME USING PAN CARD LABEL
    # -----------------------------------------------------
    #
    # Your OCR output is:
    #
    # [10] AT / - Name
    # [11] BALIREDDY BHANU PRAKASH REDDY
    #
    # Therefore we should take the line immediately
    # following the "Name" label.
    # -----------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        # Ignore "Father's Name".
        if "father" in normalized:

            continue


        # Match lines containing the PAN name label.

        if re.search(
            r"\bname\b",
            normalized,
        ):

            # If the value is on the same line:
            #
            # Name: JOHN DOE

            same_line = re.sub(
                r"(?i).*?\bname\b\s*[:\-]?\s*",
                "",
                line,
            ).strip()


            candidate = clean_name(
                same_line
            )


            if candidate:

                # Avoid accidentally using only the label.
                if candidate.lower() != "name":

                    fields["name"] = candidate

                    break


            # Otherwise use the next OCR line.

            if index + 1 < len(lines):

                next_line = lines[
                    index + 1
                ]

                candidate = clean_name(
                    next_line
                )


                if candidate:

                    fields["name"] = candidate

                    break


    # -----------------------------------------------------
    # FIND FATHER NAME
    # -----------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()


        if "father" not in normalized:

            continue


        # Same-line extraction.

        same_line = re.sub(
            r"(?i).*?father'?s?\s*name\s*[:\-]?\s*",
            "",
            line,
        ).strip()


        candidate = clean_name(
            same_line
        )


        if candidate:

            fields["father_name"] = candidate

            break


        # Next-line extraction.

        if index + 1 < len(lines):

            candidate = clean_name(
                lines[index + 1]
            )


            if candidate:

                fields["father_name"] = candidate

                break


    # -----------------------------------------------------
    # FALLBACK NAME DETECTION
    # -----------------------------------------------------
    #
    # Only used if the explicit "Name" label was not
    # detected.
    #
    # We deliberately DO NOT use the line near the DOB
    # because PAN cards can contain signatures or other
    # OCR text there.
    # -----------------------------------------------------

    if not fields["name"]:

        candidates = []

        for index, line in enumerate(lines):

            candidate = clean_name(
                line
            )

            if not candidate:

                continue


            upper = candidate.upper()


            rejected = [

                "INCOME TAX",

                "GOVT OF INDIA",

                "GOVERNMENT OF INDIA",

                "PERMANENT ACCOUNT",

                "ACCOUNT NUMBER",

                "PERMANENT ACCOUNT NUMBER",

                "FATHER NAME",

                "FATHERS NAME",

                "FATHER'S NAME",

                "DATE OF BIRTH",

                "SIGNATURE",

                "CARD",

                "DEPARTMENT",

            ]


            if any(
                word in upper
                for word in rejected
            ):

                continue


            # Never treat a PAN number as a name.

            if PAN_PATTERN.fullmatch(
                upper.replace(" ", "")
            ):

                continue


            # Don't use the line after DOB.
            if (
                index > 0
                and DOB_PATTERN.search(
                    lines[index - 1]
                )
            ):

                continue


            candidates.append(
                (index, candidate)
            )


        if candidates:

            # Prefer longer realistic names.
            candidates.sort(
                key=lambda item: (
                    len(item[1].split()),
                    len(item[1]),
                ),
                reverse=True,
            )

            fields["name"] = (
                candidates[0][1]
            )


    return fields


# =========================================================
# PAN VALIDATION
# =========================================================

def validate_pan(
    fields: dict,
) -> dict:

    errors = []

    pan_number = fields.get(
        "pan_number"
    )


    if not pan_number:

        errors.append(
            "PAN number could not be detected."
        )

    elif not PAN_PATTERN.fullmatch(
        pan_number.upper()
    ):

        errors.append(
            "Invalid PAN number format."
        )


    if not fields.get("name"):

        errors.append(
            "Name could not be detected."
        )


    if not fields.get("dob"):

        errors.append(
            "Date of birth could not be detected."
        )


    return {

        "valid": len(errors) == 0,

        "errors": errors,

        "status": (
            "verified"
            if not errors
            else "failed"
        ),

        "message": (
            "PAN information verified successfully."
            if not errors
            else "PAN verification requires review."
        ),
    }


# =========================================================
# PASSPORT VALIDATION
# =========================================================

def validate_passport(
    fields: dict,
) -> dict:

    errors = []

    if not fields.get(
        "passport_number"
    ):

        errors.append(
            "Passport number could not be detected."
        )


    return {

        "valid": len(errors) == 0,

        "errors": errors,

        "status": (
            "verified"
            if not errors
            else "failed"
        ),

        "message": (
            "Passport information detected successfully."
            if not errors
            else "Passport verification requires review."
        ),
    }


# =========================================================
# VOTER ID VALIDATION
# =========================================================

def validate_voter_id(
    fields: dict,
) -> dict:

    errors = []

    if not fields.get(
        "voter_id"
    ):

        errors.append(
            "Voter ID could not be detected."
        )


    return {

        "valid": len(errors) == 0,

        "errors": errors,

        "status": (
            "verified"
            if not errors
            else "failed"
        ),

        "message": (
            "Voter ID information detected successfully."
            if not errors
            else "Voter ID verification requires review."
        ),
    }


# =========================================================
# DRIVING LICENCE VALIDATION
# =========================================================

def validate_driving_license(
    fields: dict,
) -> dict:

    errors = []

    if not fields.get(
        "license_number"
    ):

        errors.append(
            "Driving Licence number could not be detected."
        )


    return {

        "valid": len(errors) == 0,

        "errors": errors,

        "status": (
            "verified"
            if not errors
            else "failed"
        ),

        "message": (
            "Driving Licence information detected successfully."
            if not errors
            else "Driving Licence verification requires review."
        ),
    }


# =========================================================
# UNKNOWN VALIDATION
# =========================================================

def validate_unknown(
    fields: dict,
) -> dict:

    return {

        "valid": False,

        "errors": [
            "Unsupported document type."
        ],

        "status": "unsupported",

        "message": (
            "This document type is not currently "
            "supported for verification."
        ),
    }


# =========================================================
# MAIN SERVICE
# =========================================================

def verify_document_service(
    file: UploadFile,
):

    # -----------------------------------------------------
    # FILE VALIDATION
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # SAVE FILE
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # FILE SIZE
    # -----------------------------------------------------

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

        if (
            file.content_type
            != "application/pdf"
        ):

            start = time.perf_counter()

            processed_path = preprocess_image(
                str(file_path)
            )

            print(
                "[PERFORMANCE] "
                f"Preprocessing: "
                f"{time.perf_counter() - start:.2f}s"
            )


            start = time.perf_counter()

            ocr_text = extract_text(
                processed_path
            )

            print(
                "[PERFORMANCE] "
                f"OCR: "
                f"{time.perf_counter() - start:.2f}s"
            )


        else:

            start = time.perf_counter()

            ocr_text = extract_text(
                str(file_path)
            )

            print(
                "[PERFORMANCE] "
                f"PDF OCR: "
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
            "[PERFORMANCE] "
            f"Classification: "
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


        # =================================================
        # DEFAULT RESPONSE FIELDS
        # =================================================

        fields = {

            "document_type": document_type,

            "name": None,

            "aadhaar_number": None,

            "dob": None,

            "gender": None,

            "address": None,

            "pin_code": None,

            "pan_number": None,

            "father_name": None,

            "passport_number": None,

            "nationality": None,

            "place_of_birth": None,

            "date_of_issue": None,

            "date_of_expiry": None,

            "voter_id": None,

            "epic_number": None,

            "license_number": None,

            "licence_number": None,
        }


        # =================================================
        # AADHAAR
        # =================================================

        if document_type == "aadhaar":

            start = time.perf_counter()

            aadhaar_fields = extract_fields(
                ocr_text
            )

            fields.update(
                aadhaar_fields
            )


            print(
                "[PERFORMANCE] "
                f"Aadhaar extraction: "
                f"{time.perf_counter() - start:.2f}s"
            )


            validation = validate_aadhaar(
                fields
            )


        # =================================================
        # PAN
        # =================================================

        elif document_type == "pan":

            start = time.perf_counter()

            pan_fields = extract_pan_fields(
                ocr_text
            )

            fields.update(
                pan_fields
            )


            print(
                "[PERFORMANCE] "
                f"PAN extraction: "
                f"{time.perf_counter() - start:.2f}s"
            )


            print(
                "[PAN FIELDS]",
                pan_fields,
            )


            validation = validate_pan(
                fields
            )


        # =================================================
        # PASSPORT
        # =================================================

        elif document_type == "passport":

            start = time.perf_counter()

            passport_match = re.search(
                r"\b[A-Z][0-9]{7}\b",
                full_text,
                re.IGNORECASE,
            )


            if passport_match:

                fields[
                    "passport_number"
                ] = (
                    passport_match
                    .group()
                    .upper()
                )


            dates = re.findall(
                r"\b\d{2}[/-]\d{2}[/-]\d{4}\b",
                full_text,
            )


            if len(dates) >= 1:

                fields[
                    "date_of_issue"
                ] = dates[0]


            if len(dates) >= 2:

                fields[
                    "date_of_expiry"
                ] = dates[1]


            print(
                "[PERFORMANCE] "
                f"Passport extraction: "
                f"{time.perf_counter() - start:.2f}s"
            )


            validation = validate_passport(
                fields
            )


        # =================================================
        # VOTER ID
        # =================================================

        elif document_type == "voter_id":

            start = time.perf_counter()

            epic_match = re.search(
                r"\b[A-Z]{3}[0-9]{7}\b",
                full_text,
                re.IGNORECASE,
            )


            if epic_match:

                fields["voter_id"] = (
                    epic_match
                    .group()
                    .upper()
                )

                fields["epic_number"] = (
                    epic_match
                    .group()
                    .upper()
                )


            print(
                "[PERFORMANCE] "
                f"Voter ID extraction: "
                f"{time.perf_counter() - start:.2f}s"
            )


            validation = validate_voter_id(
                fields
            )


        # =================================================
        # DRIVING LICENCE
        # =================================================

        elif document_type == "driving_license":

            start = time.perf_counter()

            patterns = [

                r"(?:dl\s*no|dl\s*number)"
                r"\s*[:\-]?\s*([A-Z0-9\-\/]+)",

                r"(?:licence\s*no|license\s*no)"
                r"\s*[:\-]?\s*([A-Z0-9\-\/]+)",

                r"(?:driving\s*licence\s*no)"
                r"\s*[:\-]?\s*([A-Z0-9\-\/]+)",
            ]


            for pattern in patterns:

                match = re.search(
                    pattern,
                    full_text,
                    re.IGNORECASE,
                )


                if match:

                    number = (
                        match
                        .group(1)
                        .upper()
                    )


                    fields[
                        "license_number"
                    ] = number


                    fields[
                        "licence_number"
                    ] = number


                    break


            print(
                "[PERFORMANCE] "
                f"Driving Licence extraction: "
                f"{time.perf_counter() - start:.2f}s"
            )


            validation = validate_driving_license(
                fields
            )


        # =================================================
        # UNKNOWN
        # =================================================

        else:

            validation = validate_unknown(
                fields
            )


        # =================================================
        # RESPONSE
        # =================================================

        print(
            "[PERFORMANCE] "
            "Document verification completed."
        )


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
                "Document processed successfully"
            ),
        }


    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


    except HTTPException:

        raise


    except Exception as exc:

        print(
            "[ERROR] "
            f"Document processing failed: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing failed. "
                "Please try again."
            ),
        ) from exc