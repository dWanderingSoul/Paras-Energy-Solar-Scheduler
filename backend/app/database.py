import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Set this in Render's environment variables to your Neon connection string, e.g.:
# postgresql://user:password@ep-xxxx.neon.tech/solarapp?sslmode=require
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./local_dev.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
