from fastapi import APIRouter, UploadFile, File
from app.services.document_service import verify_document_service

router = APIRouter()

@router.post("/verify-document")
def verify_document(file: UploadFile = File(...)):
    return verify_document_service(file)