from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentFields(BaseModel):
    """
    Normalized fields returned by all supported document extractors.
    """

    model_config = ConfigDict(extra="allow")

    # =========================================================
    # COMMON
    # =========================================================

    document_type: Optional[str] = None
    name: Optional[str] = None

    dob: Optional[str] = None
    date_of_birth: Optional[str] = None

    gender: Optional[str] = None
    sex: Optional[str] = None

    address: Optional[str] = None
    pin_code: Optional[str] = None

    # =========================================================
    # AADHAAR
    # =========================================================

    aadhaar_number: Optional[str] = None

    # =========================================================
    # PAN
    # =========================================================

    pan_number: Optional[str] = None
    father_name: Optional[str] = None

    # =========================================================
    # PASSPORT
    # =========================================================

    passport_number: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    nationality: Optional[str] = None

    place_of_birth: Optional[str] = None
    place_of_issue: Optional[str] = None

    date_of_issue: Optional[str] = None
    date_of_expiry: Optional[str] = None

    # =========================================================
    # VOTER ID
    # =========================================================

    voter_id: Optional[str] = None
    epic_number: Optional[str] = None

    # =========================================================
    # DRIVING LICENCE
    # =========================================================

    license_number: Optional[str] = None
    licence_number: Optional[str] = None

    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None

    blood_group: Optional[str] = None
    vehicle_classes: Optional[List[str]] = None

    # =========================================================
    # RELATIONSHIP FIELDS
    # =========================================================

    mother_name: Optional[str] = None
    husband_name: Optional[str] = None

    # =========================================================
    # GENERIC
    # =========================================================

    raw_text_available: Optional[bool] = None
    text_length: Optional[int] = None


class DocumentValidationResponse(BaseModel):

    valid: bool = False

    errors: List[str] = Field(
        default_factory=list
    )

    warnings: List[str] = Field(
        default_factory=list
    )

    status: Optional[str] = None

    message: Optional[str] = None

    confidence: Optional[float] = None

    # Important:
    # This project does NOT currently prove government authenticity.
    authenticity: str = "not_verified"

    checks: dict[str, Any] = Field(
        default_factory=dict
    )


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