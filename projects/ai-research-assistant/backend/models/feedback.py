"""SQLAlchemy database model for user feedback on assistant answers."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from backend.database import Base


class AnswerFeedback(Base):
    __tablename__ = "answer_feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(
        String,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )

    message_id = Column(
        Integer,
        ForeignKey("conversation_messages.id"),
        nullable=False,
        unique=True,
    )

    rating = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    comment = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", backref="feedbacks")
    conversation = relationship("Conversation", backref="feedbacks")
    message = relationship("ConversationMessage", backref="feedback", uselist=False)
