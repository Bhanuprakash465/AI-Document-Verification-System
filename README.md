# AI Document Verification System

A FastAPI application that accepts identity-document uploads (JPG, PNG, WEBP, BMP, TIFF and PDF), enhances images with OpenCV, runs DocTR OCR (AI/ML-based OCR), automatically classifies the document type with a **rule-based multi-signal classifier** (weighted keywords/identifiers/MRZ — not a trained ML classifier model), extracts document-specific fields, performs **structural/consistency validation only**, and returns a structured JSON result. A browser dashboard is served at `/app`.

> **Important limitation:** this system does **NOT** prove government authenticity. A `validated` result means the extracted fields passed format/consistency checks; `authenticity` is always `not_verified`. There is no AES-encryption, government-verification, or cryptographic-authenticity feature — do not describe it as having one.

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
UPLOAD → PREPROCESS → OCR → CLASSIFICATION → FIELD EXTRACTION → VALIDATION → JSON RESPONSE
```

1. **Upload** – extension + client-MIME allow-list, then real content/signature (magic-byte) validation; 10 MB cap **enforced while streaming** (bounded 64 KB chunks, oversize → partial file deleted + HTTP 413); path-traversal-safe filenames.
2. **Preprocess** – OpenCV document detection/crop, downscale-if-huge, upscale-if-small, grayscale/contrast/sharpen (with a minimal-mode fallback pass). Processed images are **temporary** and deleted after the response by default.
3. **OCR** – DocTR (PyTorch CPU, AI/ML-based OCR); PDFs are rasterized at bounded resolution (≤150 DPI) and capped at 5 pages; per-page line reconstruction with confidence stats and a rendered-text fallback.
4. **Classification** – **rule-based multi-signal** weighted keyword/identifier/MRZ scoring with OCR-tolerant matching (missing spaces such as `GOVERNMENT OFINDIA`, fused words such as `INCOMETAXDEPARTMENT`, and spelling variants such as `Aadhar`/`Adhaar`); returns `unknown` instead of guessing when evidence is weak. A lone 12-digit number or PAN string is never sufficient evidence on its own. The `confidence` value is a **heuristic score** (`min(0.99, 0.50 + best_score * 0.045)` with ambiguity penalty), **not** a calibrated probability.
5. **Field extraction** – one extractor module per document type, OCR-tolerant regexes and heuristics (Driving Licence handles `DOI`/`DATE OF ISSUE`/`ISSUE DATE`/`ISSUED ON`/`VALID FROM`/`VALID TILL`/`VALID UNTIL`/`VALID UPTO`/`VALID TO`/`VALIDITY` variants).
6. **Validation** – per-type **structural/consistency** checks only (number formats, required fields, date ordering, expiry warnings; Aadhaar Verhoeff checksum is a well-formedness warning, never authenticity). Statuses: `validated` (structurally valid — **not** government-authentic) / `failed` / `unsupported` / `ocr_failed`, plus per-check details and `authenticity: not_verified`.
7. **Persistence** – key result fields plus a short OCR excerpt (≤5000 chars) stored in SQLite (best-effort; never breaks the response). Uploaded originals and processed images are **deleted by default** after processing; set `RETAIN_UPLOADED_FILES=1` only for short-lived local debugging.

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
    "status": "validated",
    "errors": [],
    "warnings": [],
    "authenticity": "not_verified",
    "checks": { "pan_format": true, "name_present": true, "dob_present": true }
  },
  "message": "Document processed and structurally validated successfully. This does not prove government authenticity."
}
```

### `GET /health`

Liveness check returning `{"status": "healthy", "database": "ready|unavailable"}`. The `database` field reports SQLite reachability only — OCR availability is **not** claimed. The dashboard status pill reflects this endpoint (no static "ONLINE" claim).

### `GET /`

Service banner with links (including `/health`).

> `saved_to` / `processed_file` are retained in the response schema for backward compatibility but are `null` by default, because uploaded and processed files are deleted after processing. They are populated only when `RETAIN_UPLOADED_FILES=1` is set for local debugging.

### `GET /app/`

Browser dashboard (static frontend).

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest tests -v
```

- `tests/test_classifier.py` – classification with synthetic OCR text (all 5 types + unknown/edge cases + real-world OCR regression cases such as `GOVERNMENT OFINDIA` + heuristic-confidence check).
- `tests/test_extractors.py` – field extraction with synthetic OCR lines (all 5 types, including DL `DOI`/`Valid Till` variants and voter multiline-name regression tests).
- `tests/test_validation.py` – per-type validators, date parsing, name cleaning, Aadhaar Verhoeff-checksum warning, `validated` vs `not_verified` semantics.
- `tests/test_api.py` – synthetic in-memory API tests (health, oversize/at-limit uploads + cleanup, PDF-signature and content-spoofing rejection, corrupt-file handling, `authenticity: not_verified` invariant) plus **optional** real-document E2E tests. The real-document tests are **skipped** when local sample files are absent, so a fresh public clone shows them as `SKIPPED` — not as passed.

The public repository intentionally contains only `backend/uploads/.gitkeep` — **no real identity documents**. To run the optional E2E tests locally, place your own authorized samples in the gitignored `backend/uploads/` directory (see the header of `tests/test_api.py` for exact filenames). Synthetic tests verify logic without real documents and without mocked OCR/classification/extraction in the unit paths.

## Technology

- Backend: FastAPI, Python, OpenCV, DocTR OCR (PyTorch CPU), SQLite (SQLAlchemy), Pydantic
- Frontend: static HTML/CSS/JS dashboard (served at `/app`, no framework)
- OCR is AI/ML-based (DocTR); document classification is rule-based multi-signal scoring (not a trained classifier model).

## Privacy & retention

- Uploaded originals and generated processed images are **deleted from disk by default** after each request (`try/finally`-style cleanup on success and error paths; failures are logged, never raised). Set `RETAIN_UPLOADED_FILES=1` only for short-lived local debugging.
- SQLite stores filename, document type, verification status, timestamp, and a short OCR excerpt (≤5000 chars) — not full document dumps. The `.db` file is gitignored; never commit it.
- Server logs record counts/statuses, not full extracted identity fields.
- No database encryption, no authentication, no rate limiting are implemented — see production notes below.
- Never commit real identity documents, `.env` files, databases, or uploads. The `backend/uploads/` directory (except `.gitkeep`) is gitignored.

## CORS & production security notes

- CORS defaults to local-development origins (`127.0.0.1`/`localhost`); set the `ALLOWED_ORIGINS` environment variable (comma-separated) for production.
- Not implemented (documented as production work, not pretended features): authentication, rate limiting, request-size limits beyond the 10 MB upload cap, at-rest encryption, audit logging, official government-verification integrations.
- The unused `backend/app/models/document_detector.pt` artifact was removed (document boundary detection uses OpenCV contours). The `services/llm` helper is experimental and unused by the pipeline; core verification works without OpenAI keys or LangChain.

## Project layout

```
backend/
  app/
    main.py                     FastAPI app, CORS, static frontend mount
    routers/document.py         POST /verify-document
    services/
      image_service.py          preprocessing modes + fallbacks
      document_classifier.py    rule-based multi-signal classifier (heuristic confidence)
      document_service.py       pipeline orchestration + structural validators + persistence
      ocr/ocr_service.py        DocTR wrapper (images + bounded-PDF rasterization)
      extractor/                aadhaar / pan / passport / driving_license / voter_id
      detector/                 OpenCV document contour detection (no ML model file)
      validator/                deprecated legacy Aadhaar checks (do not extend)
      llm/verifier.py           experimental/isolated LLM hook, unused by pipeline
    database/                   SQLAlchemy engine/session/init
    models/                     ORM Document model + pydantic response models
  tests/                        pytest suite (synthetic unit/API + optional local E2E)
  uploads/                      runtime upload storage (gitignored; deleted after processing)
frontend/                       static dashboard (served at /app)
```

## Important

Use only documents you are authorized to process. This project performs field extraction and basic consistency checks; a `validated` result is **not** proof of document authenticity (`authenticity` stays `not_verified`). CORS is restricted to local-development origins by default (configure `ALLOWED_ORIGINS` in production). Production deployments should additionally add authentication, encryption, retention/deletion rules, audit logging, rate limiting and official verification-provider integrations.