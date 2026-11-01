"""SQLAlchemy model for Transactional Outbox pattern event records."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from backend.database import Base


class OutboxEvent(Base):
    """Transactional Outbox event record stored atomically with business changes."""

    __tablename__ = "outbox_events"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    event_type = Column(
        String,
        nullable=False,
        index=True
    )
    event_version = Column(
        Integer,
        nullable=False,
        default=1
    )
    aggregate_id = Column(
        String,
        nullable=False,
        index=True
    )
    correlation_id = Column(
        String,
        nullable=True,
        index=True
    )
    payload = Column(
        Text,
        nullable=False
    )
    status = Column(
        String,
        nullable=False,
        default="pending",
        index=True
    )  # pending, publishing, published, failed, dead_letter
    retry_count = Column(
        Integer,
        nullable=False,
        default=0
    )
    max_retries = Column(
        Integer,
        nullable=False,
        default=3
    )
    last_error = Column(
        Text,
        nullable=True
    )
    claimed_at = Column(
        DateTime,
        nullable=True
    )
    published_at = Column(
        DateTime,
        nullable=True
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_outbox_events_status_created", "status", "created_at"),
    )
