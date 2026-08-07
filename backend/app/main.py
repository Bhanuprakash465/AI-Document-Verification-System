from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.document import router as document_router
from app.database.init_db import create_tables

app = FastAPI(
    title="AI Document Verification System",
    version="1.0.0",
    description="Upload an identity document to extract and validate Aadhaar fields.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    }
