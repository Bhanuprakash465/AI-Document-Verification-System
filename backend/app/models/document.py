from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String, nullable=False)

    document_type = Column(String)

    extracted_text = Column(String)

    verification_status = Column(String)

    uploaded_at = Column(DateTime, default=datetime.utcnow)