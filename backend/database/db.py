# Database connection and operations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database.models import Base
from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()