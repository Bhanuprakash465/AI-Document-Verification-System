# AI Document Verification System

A FastAPI application for processing Aadhaar documents. It accepts JPG, PNG and PDF uploads, enhances image documents with OpenCV, uses DocTR OCR to extract text, identifies Aadhaar fields, and reports validation results in structured JSON.

## Features

- Upload API: `POST /verify-document`
- Browser dashboard at `/app`
- JPG, PNG and PDF support (10 MB maximum)
- Perspective correction, contrast enhancement and denoising for images
- Aadhaar number, name, DOB, gender, PIN code and address extraction
- Required-field and format validation
- Unique server-side filenames to prevent uploads from overwriting one another

## Run locally

Requires Python 3.10–3.12. From the repository root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/app](http://127.0.0.1:8000/app) for the dashboard, or [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the API documentation. The first OCR request may download DocTR model weights.

## API response

```json
{
  "fields": {
    "document_type": "Aadhaar",
    "name": "Example Person",
    "aadhaar_number": "1234 5678 9012",
    "dob": "04/06/2005",
    "gender": "Male",
    "pin_code": "515425"
  },
  "validation": { "valid": true, "errors": [] }
}
```

## Important

Use only documents you are authorized to process. This project performs field extraction and basic consistency checks; a valid result is not proof of document authenticity. Production deployments should add authentication, encryption, retention/deletion rules, audit logging, rate limiting and official verification-provider integrations.
