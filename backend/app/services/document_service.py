from fastapi import UploadFile, HTTPException
from app.services.image_service import preprocess_image
import shutil
import os

UPLOAD_FOLDER = "uploads"

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

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    processed_path = None

    if file.content_type != "application/pdf":
        processed_path = preprocess_image(file_path)
    return {
    "filename": file.filename,
    "content_type": file.content_type,
    "saved_to": file_path,
    "processed_file": processed_path,
    "message": "File uploaded and preprocessed successfully"
}