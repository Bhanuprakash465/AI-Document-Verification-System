from typing import List, Optional

from pydantic import BaseModel, Field


class DocumentFields(BaseModel):

    # Common
    document_type: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    pin_code: Optional[str] = None

    # Aadhaar
    aadhaar_number: Optional[str] = None

    # PAN
    pan_number: Optional[str] = None
    father_name: Optional[str] = None

    # Passport
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    place_of_birth: Optional[str] = None
    date_of_issue: Optional[str] = None
    date_of_expiry: Optional[str] = None

    # Voter ID
    voter_id: Optional[str] = None
    epic_number: Optional[str] = None

    # Driving Licence
    license_number: Optional[str] = None
    licence_number: Optional[str] = None

    # Generic / unsupported documents
    raw_text_available: Optional[bool] = None
    text_length: Optional[int] = None


class DocumentValidationResponse(BaseModel):

    valid: bool = False

    errors: List[str] = Field(
        default_factory=list
    )

    status: Optional[str] = None

    message: Optional[str] = None

    confidence: Optional[float] = None


class DocumentVerifyResponse(BaseModel):

    filename: str

    content_type: str

    saved_to: str

    processed_file: Optional[str] = None

    document_type: Optional[str] = None

    document: Optional[dict] = None

    ocr_text: List[str] = Field(
        default_factory=list
    )

    fields: DocumentFields = Field(
        default_factory=DocumentFields
    )

    validation: DocumentValidationResponse = Field(
        default_factory=DocumentValidationResponse
    )

    message: str