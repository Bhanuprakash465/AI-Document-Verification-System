# AI Document Verification System

A FastAPI application that accepts identity-document uploads (JPG, PNG, WEBP, BMP, TIFF and PDF), enhances images with OpenCV, runs DocTR OCR, automatically classifies the document type, extracts document-specific fields, validates them, and returns a structured JSON result. A browser dashboard is served at `/app`.

## Supported document types

| Type | Identifier format | Extracted fields |
|------|-------------------|------------------|
| Aadhaar Card | `1234 5678 9012` | Aadhaar number, name, DOB, gender, address, PIN code |
| PAN Card | `AAAAA9999A` | PAN number, name, father's name, DOB |
| Passport (India) | `A9999999` + MRZ | Passport number, surname, given names, nationality, place of birth/issue, dates, MRZ lines |
| Driving Licence | state-specific | Licence number, name, DOB, issue/expiry dates, blood group, vehicle classes |
| Voter ID (EPIC) | `ABC1234567` | EPIC number, name, relative's name, DOB |

Other document types (ration card, vehicle RC, GST certificate, etc.) are detected and reported as `unsupported` rather than misclassified.

## Pipeline

```
UPLOAD → PREPROCESS → OCR → CLASSIFICATION → FIELD EXTRACTION → VALIDATION → VERIFICATION → JSON RESPONSE
```

1. **Upload** – type/extension allow-list, 10 MB cap, path-traversal-safe filenames.
2. **Preprocess** – document detection/crop, downscale-if-huge, upscale-if-small, grayscale/contrast/sharpen (with a minimal-mode fallback pass).
3. **OCR** – DocTR (PyTorch CPU); PDFs are rasterized and capped at 5 pages; per-page line reconstruction with confidence stats and a rendered-text fallback.
4. **Classification** – weighted keyword/identifier/MRZ scoring with OCR-tolerant matching (missing spaces such as `GOVERNMENT OFINDIA`, fused words such as `INCOMETAXDEPARTMENT`, and spelling variants such as `Aadhar`/`Adhaar`); returns `unknown` instead of guessing when evidence is weak. A lone 12-digit number or PAN string is never sufficient evidence on its own.
5. **Field extraction** – one extractor module per document type, OCR-tolerant regexes and heuristics.
6. **Validation** – per-type structural checks (number formats, required fields, date ordering, expiry warnings).
7. **Verification** – aggregated status (`verified` / `failed` / `unsupported` / `ocr_failed`) plus per-check details.
8. **Persistence** – every result is stored in SQLite (best-effort; never breaks the response).

## Run locally

Requires Python 3.10–3.12. From the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- Dashboard: [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- The first OCR request downloads DocTR model weights.

## API

### `POST /verify-document`

Upload a document as multipart form field `file`. Example:

```powershell
curl -X POST http://127.0.0.1:8000/verify-document -F "file=@pan.pdf;type=application/pdf"
```

Response (abridged):

```json
{
  "filename": "pan.pdf",
  "document_type": "pan",
  "display_name": "PAN Card",
  "confidence": 0.93,
  "ocr_text": ["Income Tax Department", "..."],
  "fields": {
    "document_type": "pan",
    "name": "EXAMPLE PERSON",
    "pan_number": "ABCPD1234E",
    "dob": "14/02/1995"
  },
  "validation": {
    "valid": true,
    "status": "verified",
    "errors": [],
    "warnings": [],
    "checks": { "pan_format": true, "name_present": true, "dob_present": true }
  },
  "message": "Document processed and verified successfully."
}
```

### `GET /`

Service banner with links. Response paths (`saved_to`, `processed_file`) are returned relative to the backend directory — absolute server filesystem paths are never exposed.

### `GET /app/`

Browser dashboard (static frontend).

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```

- `tests/test_classifier.py` – classification with synthetic OCR text (all 5 types + unknown/edge cases + real-world OCR regression cases such as `GOVERNMENT OFINDIA`).
- `tests/test_extractors.py` – field extraction with synthetic OCR lines (all 5 types).
- `tests/test_validation.py` – per-type validators, date parsing, name cleaning.
- `tests/test_api.py` – end-to-end pipeline through the API using **real sample documents** in `backend/uploads/` (Aadhaar image, PAN PDF, passport image) plus database-persistence and error-handling checks. Skips automatically if a sample file is missing.

The synthetic tests verify logic without real documents; the API tests run the genuine OCR pipeline against real files — no mocked OCR/classification/extraction anywhere.

## Project layout

```
backend/
  app/
    main.py                     FastAPI app, CORS, static frontend mount
    routers/document.py         POST /verify-document
    services/
      image_service.py          preprocessing modes + fallbacks
      document_classifier.py    weighted multi-signal classifier
      document_service.py       pipeline orchestration + validators + persistence
      ocr/ocr_service.py        DocTR wrapper (images + PDFs)
      extractor/                aadhaar / pan / passport / driving_license / voter_id
      detector/                 document contour detection
      validator/                legacy Aadhaar validator
      llm/verifier.py           optional LLM verification (lazy import)
    database/                   SQLAlchemy engine/session/init
    models/                     ORM Document model + pydantic response models
  tests/                        pytest suite (unit + real-document API tests)
  uploads/                      runtime upload storage (gitignored)
frontend/                       static dashboard (served at /app)
```

## Important

Use only documents you are authorized to process. This project performs field extraction and basic consistency checks; a valid result is **not** proof of document authenticity. Production deployments should add authentication, encryption, retention/deletion rules, audit logging, rate limiting and official verification-provider integrations.