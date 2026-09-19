"""
API integration tests.

Most tests below use synthetic in-memory uploads (bytes constructed in
the test itself) so they run on a fresh public clone with no private
files. Tests that need REAL local sample documents in
``backend/uploads/`` are marked and skipped gracefully when those files
are absent — the public repository intentionally contains only
``backend/uploads/.gitkeep`` (never commit real identity documents).

To run the real-document E2E tests locally, place your own authorized
samples in ``backend/uploads/`` (gitignored) with the expected names:

  * Aadhaar : uploads/adhar card.jpeg.jpg
  * PAN     : uploads/26d6e93931ee41cf99b291c59887a8fe_pan (1).pdf
  * Passport: uploads/25c862700038402a9c38a5df8099f339_indianpp.jpg
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
        "validated",
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
        "validated",
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
        "validated",
        "failed",
    )


# =========================================================
# SYNTHETIC API TESTS (run on any fresh clone, no real docs)
# =========================================================

import io

from PIL import Image, ImageDraw


def _make_test_image_bytes(fmt="PNG", size=(900, 900)):
    image = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([60, 60, size[0] - 60, size[1] - 60], outline="black", width=4)
    draw.text((120, 120), "SYNTHETIC TEST DOCUMENT", fill="black")
    draw.text((120, 200), "No real personal data.", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database"] in ("ready", "unavailable")


def test_home_lists_health():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/health"


def test_oversized_upload_rejected_and_cleaned():
    from app.services.document_service import MAX_FILE_SIZE, UPLOAD_FOLDER

    before = set(p.name for p in UPLOAD_FOLDER.glob("*") if p.is_file())
    big = b"x" * (MAX_FILE_SIZE + 1024)
    response = client.post(
        "/verify-document",
        files={"file": ("big.png", big, "image/png")},
    )
    assert response.status_code == 413
    after = set(p.name for p in UPLOAD_FOLDER.glob("*") if p.is_file())
    # No partial file may remain (other than pre-existing local samples).
    assert after <= before


def test_at_limit_upload_size_accepted_by_stream_writer():
    # Direct unit check of the bounded streaming writer (no OCR involved).
    import tempfile

    from app.services.document_service import MAX_FILE_SIZE, _save_upload_bounded

    class _FakeUpload:
        def __init__(self, payload: bytes):
            self.file = io.BytesIO(payload)

    with tempfile.TemporaryDirectory() as tmp:
        from pathlib import Path as _Path

        target = _Path(tmp) / "at_limit.bin"
        payload = b"y" * MAX_FILE_SIZE
        written = _save_upload_bounded(_FakeUpload(payload), target)
        assert written == MAX_FILE_SIZE
        assert target.stat().st_size == MAX_FILE_SIZE
        over = _FakeUpload(b"z" * (MAX_FILE_SIZE + 1))
        try:
            _save_upload_bounded(over, _Path(tmp) / "over.bin")
            raise AssertionError("expected HTTP 413")
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 413
            assert not (_Path(tmp) / "over.bin").exists()


def test_pdf_signature_rejected():
    response = client.post(
        "/verify-document",
        files={"file": ("fake.pdf", b"not a pdf at all", "application/pdf")},
    )
    assert response.status_code == 400


def test_exe_content_masquerading_as_image_rejected():
    response = client.post(
        "/verify-document",
        files={"file": ("evil.png", b"MZ" + b"\x00" * 100, "image/png")},
    )
    assert response.status_code == 400


def test_corrupt_image_rejected_cleanly():
    response = client.post(
        "/verify-document",
        files={
            "file": ("broken.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, "image/png")
        },
    )
    # Must be a clean 4xx, never a 500 with a stack trace.
    assert response.status_code in (400, 413, 422, 503)


def test_validation_status_never_claims_authenticity():
    # Synthetic image will OCR-fail or classify unknown, but whatever the
    # branch, authenticity must stay "not_verified".
    payload = _make_test_image_bytes()
    response = client.post(
        "/verify-document",
        files={"file": ("synthetic.png", payload, "image/png")},
    )
    assert response.status_code in (200, 400, 503)
    if response.status_code == 200:
        body = response.json()
        assert body["validation"]["authenticity"] == "not_verified"
        # Temp files are cleaned up by default; no server paths leaked.
        assert body["saved_to"] is None
        assert body["processed_file"] is None


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