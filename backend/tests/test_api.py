"""
API integration tests.

These tests run the REAL pipeline (preprocess -> OCR ->
classification -> extraction -> validation) against REAL sample
documents found in backend/uploads/. They are slower than unit
tests because DocTR model weights are loaded on first use.

Real sample files used (skipped gracefully if missing):
  * Aadhaar : uploads/adhar card.jpeg.jpg
  * PAN     : uploads/26d6e93931ee41cf99b291c59887a8fe_pan (1).pdf
  * Passport: uploads/25c862700038402a9c38a5df8099f339_indianpp.jpg

Driving Licence and Voter ID have no real samples in the repo;
those document types are covered by the synthetic-text unit tests
in test_classifier.py / test_extractors.py / test_validation.py.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
UPLOADS = BACKEND_DIR / "uploads"

AADHAAR_SAMPLE = UPLOADS / "adhar card.jpeg.jpg"
PAN_SAMPLE = UPLOADS / "26d6e93931ee41cf99b291c59887a8fe_pan (1).pdf"
PASSPORT_SAMPLE = UPLOADS / "25c862700038402a9c38a5df8099f339_indianpp.jpg"

client = TestClient(app)


# =========================================================
# BASIC ENDPOINTS
# =========================================================

def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_verify_document_requires_file():
    response = client.post("/verify-document")
    assert response.status_code == 422


def test_verify_document_rejects_unsupported_type():
    response = client.post(
        "/verify-document",
        files={
            "file": (
                "malware.exe",
                b"MZ fake binary",
                "application/x-msdownload",
            )
        },
    )
    assert response.status_code == 400


# =========================================================
# REAL DOCUMENT PIPELINE TESTS
# =========================================================

@pytest.mark.skipif(
    not AADHAAR_SAMPLE.exists(),
    reason="Real Aadhaar sample not present in uploads/",
)
def test_real_aadhaar_pipeline():
    with open(AADHAAR_SAMPLE, "rb") as handle:
        response = client.post(
            "/verify-document",
            files={
                "file": (
                    AADHAAR_SAMPLE.name,
                    handle.read(),
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()

    # OCR must have produced text.
    assert len(body["ocr_text"]) > 0

    # Classification must recognise Aadhaar.
    assert body["document_type"] == "aadhaar"

    # Field extraction must find the Aadhaar number.
    assert body["fields"]["aadhaar_number"]

    # Validation must have run and produced a status.
    assert body["validation"]["status"] in (
        "verified",
        "failed",
    )


@pytest.mark.skipif(
    not PAN_SAMPLE.exists(),
    reason="Real PAN sample not present in uploads/",
)
def test_real_pan_pipeline():
    with open(PAN_SAMPLE, "rb") as handle:
        response = client.post(
            "/verify-document",
            files={
                "file": (
                    PAN_SAMPLE.name,
                    handle.read(),
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert len(body["ocr_text"]) > 0
    assert body["document_type"] == "pan"
    assert body["fields"]["pan_number"]
    assert body["validation"]["status"] in (
        "verified",
        "failed",
    )


@pytest.mark.skipif(
    not PASSPORT_SAMPLE.exists(),
    reason="Real passport sample not present in uploads/",
)
def test_real_passport_pipeline():
    with open(PASSPORT_SAMPLE, "rb") as handle:
        response = client.post(
            "/verify-document",
            files={
                "file": (
                    PASSPORT_SAMPLE.name,
                    handle.read(),
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200
    body = response.json()

    assert len(body["ocr_text"]) > 0
    assert body["document_type"] == "passport"
    assert body["fields"]["passport_number"]
    assert body["validation"]["status"] in (
        "verified",
        "failed",
    )


# =========================================================
# DATABASE PERSISTENCE CHECK
# =========================================================

@pytest.mark.skipif(
    not AADHAAR_SAMPLE.exists(),
    reason="Real Aadhaar sample not present in uploads/",
)
def test_verification_persisted_to_database():
    from sqlalchemy import select

    from app.database.database import SessionLocal
    from app.models.document import Document

    with open(AADHAAR_SAMPLE, "rb") as handle:
        response = client.post(
            "/verify-document",
            files={
                "file": (
                    AADHAAR_SAMPLE.name,
                    handle.read(),
                    "image/jpeg",
                )
            },
        )

    assert response.status_code == 200

    db = SessionLocal()
    try:
        record = db.execute(
            select(Document)
            .order_by(Document.id.desc())
            .limit(1)
        ).scalar_one_or_none()

        assert record is not None
        assert record.document_type == "aadhaar"
        assert record.verification_status
        assert record.extracted_text
    finally:
        db.close()