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

    # Alias emitted by the passport extractor (and normalised in
    # document_service) alongside ``given_names``.
    given_name: Optional[str] = None

    # MRZ vs visual-OCR date disagreements are surfaced as warnings
    # instead of being silently resolved.
    date_warnings: Optional[List[str]] = None

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

    # NOTE: "validated" means the extracted fields passed
    # structural/consistency checks only. It does NOT mean the document
    # is genuine or government-issued. Authenticity is tracked separately
    # and stays "not_verified" (no authenticity verification exists).

    errors: List[str] = Field(
        default_factory=list
    )

    warnings: List[str] = Field(
        default_factory=list
    )

    status: Optional[str] = None

    message: Optional[str] = None

    confidence: Optional[float] = None
    """Heuristic classification confidence in [0, 1].

    This is NOT a calibrated statistical probability — it is a
    monotonic function of the rule-based classifier score
    (``0.50 + best_score * 0.045``, capped at 0.99, with an ambiguity
    penalty). Higher means more matching signals, not a measured
    likelihood.
    """

    # Important:
    # This project does NOT currently prove government authenticity.
    authenticity: str = "not_verified"

    checks: dict[str, Any] = Field(
        default_factory=dict
    )


class DocumentVerifyResponse(BaseModel):

    filename: str

    # Optional: some HTTP clients (e.g. plain curl without an explicit
    # -F "file=...;type=..." part) send no Content-Type at all, which
    # means UploadFile.content_type is None. Making this Optional
    # avoids a 500 (pydantic response validation error) on an
    # otherwise perfectly valid upload.
    content_type: Optional[str] = None

    # File-system paths are no longer retained by default: uploads and
    # processed images are deleted after processing (see
    # RETAIN_UPLOADED_FILES). These fields stay Optional for backward
    # compatibility and are None unless retention is explicitly enabled.
    saved_to: Optional[str] = None

    processed_file: Optional[str] = None

    document_type: Optional[str] = None

    # Top-level classification convenience fields so API consumers
    # (and the frontend) do not have to reach into nested objects.
    # NOTE: this confidence is a heuristic rule-based score, not a
    # calibrated probability (see DocumentValidationResponse).
    display_name: Optional[str] = None

    confidence: Optional[float] = None

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