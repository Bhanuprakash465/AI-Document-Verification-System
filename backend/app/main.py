from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.document import router as document_router
from app.database.init_db import create_tables

app = FastAPI(
    title="AI Document Verification System",
    version="1.0.0",
    description=(
        "Upload an identity document to extract fields and perform "
        "structural/consistency validation. This system does NOT prove "
        "government authenticity."
    ),
)

# CORS is intentionally permissive for local development so the static
# dashboard served at /app can call the API without extra setup.
# For production, set ALLOWED_ORIGINS (comma-separated) to the exact
# origins that should be allowed, e.g.
#   ALLOWED_ORIGINS=https://verify.example.com
# When unset, local development origins are used.
_configured_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
_allow_origins = _configured_origins or [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
create_tables()

app.include_router(document_router)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


@app.get("/")
def home():
    return {
        "message": "Welcome to AI Document Verification System",
        "docs": "/docs",
        "web_app": "/app",
        "health": "/health",
    }


@app.get("/health")
def health():
    """Liveness check. Reports database reachability without claiming OCR status."""
    database = "unknown"
    try:
        from sqlalchemy import text

        from app.database.database import engine

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ready"
    except Exception:
        database = "unavailable"
    return {"status": "healthy", "database": database}
