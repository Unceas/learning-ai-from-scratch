"""SQLAlchemy database models for persistence."""

from sqlalchemy import Column, String
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        String,
        primary_key=True
    )

    password_hash = Column(
        String,
        nullable=False
    )
