from pydantic import BaseModel
from typing import List, Optional


class DocumentVerifyRequest(BaseModel):
    filename: str
    content_type: str
    saved_to: str
    processed_file: Optional[str]
    ocr_text: List[str]


class AadhaarData(BaseModel):
    aadhaar_number: Optional[str]
    name: Optional[str]
    dob: Optional[str]
    address: Optional[str]
