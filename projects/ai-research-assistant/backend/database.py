"""Database engine, declarative base, and session dependency provider for SQLite/SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """Yield a database session and guarantee cleanup on completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
