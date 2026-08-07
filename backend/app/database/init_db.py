from app.database.database import Base, engine

# Import all models here
from app.models.document import Document


def create_tables():
    Base.metadata.create_all(bind=engine)
    