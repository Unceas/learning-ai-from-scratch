"""Service layer for conversation management and message persistence."""

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models.conversation import Conversation, ConversationMessage

MAX_HISTORY_MESSAGES = 10


def create_conversation(
    db: Session,
    user_id: str,
    title: Optional[str] = None
) -> Conversation:
    """Create a new conversation record for an authenticated user."""
    conversation = Conversation(
        user_id=user_id,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_conversation(
    db: Session,
    user_id: str,
    conversation_id: int
) -> Optional[Conversation]:
    """Retrieve a conversation ensuring strict multi-tenant isolation.
    
    Security pattern:
    Both conversation_id and user_id are required in the filter so that
    unauthorized users cannot access or tamper with other users' conversations.
    """
    return (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )


def list_conversations(
    db: Session,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Conversation]:
    """List conversations belonging to the authenticated user."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def delete_conversation(
    db: Session,
    user_id: str,
    conversation_id: int
) -> bool:
    """Delete a conversation belonging to the authenticated user."""
    conversation = get_conversation(db, user_id, conversation_id)
    if not conversation:
        return False
    db.delete(conversation)
    db.commit()
    return True


def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
) -> ConversationMessage:
    """Persist a conversation message (user or assistant)."""
    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(
    db: Session,
    conversation_id: int,
    limit: int = MAX_HISTORY_MESSAGES,
) -> List[ConversationMessage]:
    """Retrieve recent conversation history in chronological order.
    
    Caps history at `limit` (default: 10) to avoid unbounded context expansion.
    """
    return (
        db.query(ConversationMessage)
        .filter(
            ConversationMessage.conversation_id == conversation_id
        )
        .order_by(
            ConversationMessage.id.desc()
        )
        .limit(limit)
        .all()
    )[::-1]
