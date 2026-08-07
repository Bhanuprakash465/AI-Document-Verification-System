from fastapi import APIRouter, File, UploadFile
from app.models.response import DocumentVerifyResponse
from app.services.document_service import verify_document_service

router = APIRouter(tags=["Document verification"])

@router.post("/verify-document", response_model=DocumentVerifyResponse)
def verify_document(file: UploadFile = File(...)):
    return verify_document_service(file)
