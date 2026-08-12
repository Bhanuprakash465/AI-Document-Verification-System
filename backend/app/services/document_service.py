from pathlib import Path
from uuid import uuid4
import shutil
import time

from fastapi import HTTPException, UploadFile

from app.services.image_service import preprocess_image
from app.services.ocr import extract_text
from app.services.extractor import extract_fields
from app.services.validator import validate_aadhaar


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

UPLOAD_FOLDER = (
    Path(__file__).resolve().parents[2] /
    "uploads"
)

MAX_FILE_SIZE = 10 * 1024 * 1024


ALLOWED_TYPES = {
    "image/jpeg",
    "image/png",
    "application/pdf"
}


# ---------------------------------------------------------
# Main verification service
# ---------------------------------------------------------

def verify_document_service(
    file: UploadFile
):

    # -----------------------------------------------------
    # Validate file type
    # -----------------------------------------------------

    if file.content_type not in ALLOWED_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only JPG, PNG and PDF files "
                "are allowed."
            )
        )


    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="A filename is required."
        )


    # -----------------------------------------------------
    # Create upload directory
    # -----------------------------------------------------

    UPLOAD_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )


    # -----------------------------------------------------
    # Create safe filename
    # -----------------------------------------------------

    safe_name = Path(
        file.filename
    ).name


    file_path = (
        UPLOAD_FOLDER /
        f"{uuid4().hex}_{safe_name}"
    )


    # -----------------------------------------------------
    # Save uploaded file
    # -----------------------------------------------------

    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    # -----------------------------------------------------
    # Check file size
    # -----------------------------------------------------

    if file_path.stat().st_size > MAX_FILE_SIZE:

        file_path.unlink(
            missing_ok=True
        )

        raise HTTPException(
            status_code=413,
            detail=(
                "The file must be "
                "10 MB or smaller."
            )
        )


    processed_path = None


    try:

        # =================================================
        # IMAGE PROCESSING
        # =================================================

        if file.content_type != "application/pdf":

            start = time.perf_counter()


            processed_path = preprocess_image(
                str(file_path)
            )


            preprocessing_time = (
                time.perf_counter() -
                start
            )


            print(
                f"[PERFORMANCE] "
                f"Preprocessing: "
                f"{preprocessing_time:.2f}s"
            )


            # =============================================
            # OCR
            # =============================================

            start = time.perf_counter()


            ocr_text = extract_text(
                processed_path
            )


            ocr_time = (
                time.perf_counter() -
                start
            )


            print(
                f"[PERFORMANCE] "
                f"OCR: "
                f"{ocr_time:.2f}s"
            )


        # =================================================
        # PDF PROCESSING
        # =================================================

        else:

            start = time.perf_counter()


            ocr_text = extract_text(
                str(file_path)
            )


            ocr_time = (
                time.perf_counter() -
                start
            )


            print(
                f"[PERFORMANCE] "
                f"PDF OCR: "
                f"{ocr_time:.2f}s"
            )


        # =================================================
        # FIELD EXTRACTION
        # =================================================

        start = time.perf_counter()


        fields = extract_fields(
            ocr_text
        )


        extraction_time = (
            time.perf_counter() -
            start
        )


        print(
            f"[PERFORMANCE] "
            f"Extraction: "
            f"{extraction_time:.2f}s"
        )


        # =================================================
        # VALIDATION
        # =================================================

        start = time.perf_counter()


        validation = validate_aadhaar(
            fields
        )


        validation_time = (
            time.perf_counter() -
            start
        )


        print(
            f"[PERFORMANCE] "
            f"Validation: "
            f"{validation_time:.2f}s"
        )


        # =================================================
        # TOTAL PROCESSING TIME
        # =================================================

        print(
            "[PERFORMANCE] "
            "Document verification completed."
        )


        # =================================================
        # RESPONSE
        # =================================================

        return {

            "filename": safe_name,

            "content_type": (
                file.content_type
            ),

            "saved_to": str(
                file_path
            ),

            "processed_file": (
                str(processed_path)
                if processed_path
                else None
            ),

            "ocr_text": ocr_text,

            "fields": fields,

            "validation": validation,

            "message": (
                "Document processed "
                "successfully"
            )

        }


    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc)
        ) from exc


    except HTTPException:

        raise


    except Exception as exc:

        print(
            "[ERROR] "
            f"Document processing failed: "
            f"{exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Document processing failed. "
                "Please try again."
            )
        ) from exc