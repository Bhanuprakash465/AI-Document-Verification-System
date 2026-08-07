from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from app.services.image_service import preprocess_image
from app.services.ocr import extract_text
from app.services.extractor import extract_fields
from app.services.validator import validate_aadhaar

import shutil

UPLOAD_FOLDER = Path(__file__).resolve().parents[2] / "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_TYPES = [
    "image/jpeg",
    "image/png",
    "application/pdf"
]


def verify_document_service(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and PDF files are allowed."
        )

    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")

    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    file_path = UPLOAD_FOLDER / f"{uuid4().hex}_{safe_name}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    if file_path.stat().st_size > MAX_FILE_SIZE:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="The file must be 10 MB or smaller.")

    processed_path = None
    ocr_text = []

    try:
        if file.content_type != "application/pdf":
            processed_path = preprocess_image(str(file_path))
            ocr_text = extract_text(processed_path)
        else:
            ocr_text = extract_text(str(file_path))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    fields = extract_fields(ocr_text)
    validation = validate_aadhaar(fields)

    return {

        "filename": safe_name,

        "content_type": file.content_type,

        "saved_to": str(file_path),

        "processed_file": str(processed_path) if processed_path else None,

        "ocr_text": ocr_text,

        "fields": fields,

        "validation": validation,

        "message": "Document processed successfully"
    }
