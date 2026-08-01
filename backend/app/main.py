from fastapi import FastAPI
from app.routers.document import router as document_router
app = FastAPI()

app.include_router(document_router)

@app.get("/")
def home():
    return {
        "message": "Welcome to AI Document Verification System"
    }