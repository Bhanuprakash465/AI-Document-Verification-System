from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    filename: str
    document_type: str | None = None
    extracted_text: str | None = None
    verification_status: str | None = None
    uploaded_at: datetime

    class Config:
        from_attributes = True