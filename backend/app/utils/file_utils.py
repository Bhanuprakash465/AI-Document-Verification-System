import os
from fastapi import UploadFile, HTTPException

ALLOWED_TYPES = [
    "image/jpeg",
    "image/png",
    "application/pdf"
]

UPLOAD_FOLDER = "uploads"


def validate_file(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG and PDF files are allowed."
        )


def save_file(file: UploadFile):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(file.file.read())

    return file_path