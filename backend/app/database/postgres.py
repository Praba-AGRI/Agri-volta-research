import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config.settings import settings

db_url = settings.DATABASE_URL
try:
    engine = create_engine(db_url, connect_args={"connect_timeout": 2} if "postgresql" in db_url else {})
    # Test connection
    with engine.connect() as conn:
        pass
except Exception:
    # Fallback to local SQLite if PostgreSQL is unavailable locally
    os.makedirs("./data", exist_ok=True)
    sqlite_url = "sqlite:///./data/agrivoltaics_metadata.db"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
