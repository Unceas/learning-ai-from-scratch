"""SQLAlchemy database models for persistence."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey
)
from sqlalchemy.orm import relationship
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

    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False
    )

    file_hash = Column(
        String,
        nullable=False
    )

    filename = Column(
        String,
        nullable=False
    )

    chunks = Column(
        Integer,
        nullable=False,
        default=0
    )

    status = Column(
        String,
        nullable=False,
        default="indexed"
    )

    user = relationship(
        "User",
        back_populates="documents"
    )
