from pydantic import BaseModel
from typing import List, Optional


class AadhaarFields(BaseModel):
    document_type: Optional[str]
    name: Optional[str]
    aadhaar_number: Optional[str]
    dob: Optional[str]
    gender: Optional[str]
    address: Optional[str]
    pin_code: Optional[str]


class AadhaarValidationResponse(BaseModel):
    valid: bool
    errors: List[str] = []


class DocumentVerifyResponse(BaseModel):
    filename: str
    content_type: str
    saved_to: str
    processed_file: Optional[str]
    ocr_text: List[str]
    fields: AadhaarFields
    validation: AadhaarValidationResponse
    message: str
