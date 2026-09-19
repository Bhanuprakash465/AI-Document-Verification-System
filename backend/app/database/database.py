from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Absolute, machine-independent database location: always the
# ``backend/`` directory, regardless of the process working
# directory that uvicorn happens to be started from.
BACKEND_DIR = Path(__file__).resolve().parents[2]

DATABASE_URL = "sqlite:///" + str(
    BACKEND_DIR / "document_verification.db"
).replace("\\", "/")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()