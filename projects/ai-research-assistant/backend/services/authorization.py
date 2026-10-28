"""Centralized authorization service enforcing strict user ownership and object relationships.

Every document, chunk, conversation, message, source excerpt, and feedback record
must be verified against the authenticated user on the backend. A frontend-supplied
user ID, an opaque object ID, or a cache hit is never proof of authorization.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.exceptions import DocumentNotFoundError
from backend.models import Document
from backend.models.conversation import Conversation, ConversationMessage
from backend.models.feedback import AnswerFeedback

logger = logging.getLogger(__name__)


def get_owned_document(
    db: Session,
    user_id: str,
    document_id: int | str,
    require_indexed: bool = False,
) -> Document:
    """Retrieve a document owned by the authenticated user, or raise 404.

    Args:
        db: Active SQLAlchemy database session.
        user_id: Authenticated user identifier from verified JWT.
        document_id: Numeric document ID or SHA-256 file_hash string.
        require_indexed: If True, requires document.status == 'indexed'.

    Returns:
        Authorized Document model instance.

    Raises:
        DocumentNotFoundError / HTTPException(404): If missing or not owned by user.
        HTTPException(404): If require_indexed is True and status != 'indexed'.
    """
    query = db.query(Document).filter(Document.user_id == user_id)

    if isinstance(document_id, int) or (isinstance(document_id, str) and document_id.isdigit()):
        document = query.filter(Document.id == int(document_id)).first()
    else:
        document = query.filter(Document.file_hash == str(document_id)).first()

    if document is None:
        logger.warning(
            "Access denied: document=%s not found or not owned by user=%s",
            document_id,
            user_id,
        )
        raise DocumentNotFoundError()

    if require_indexed and document.status != "indexed":
        logger.warning(
            "Access denied: document=%s owned by user=%s is not indexed (status=%s)",
            document_id,
            user_id,
            document.status,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or not indexed.",
        )

    return document


def get_owned_conversation(
    db: Session,
    user_id: str,
    conversation_id: int | str,
) -> Conversation:
    """Retrieve a conversation owned by the authenticated user, or raise 404.

    Args:
        db: Active SQLAlchemy database session.
        user_id: Authenticated user identifier from verified JWT.
        conversation_id: Integer or string conversation ID.

    Returns:
        Authorized Conversation model instance.

    Raises:
        HTTPException(404): If conversation does not exist or belongs to another user.
    """
    try:
        conv_id = int(conversation_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conv_id,
            Conversation.user_id == user_id,
        )
        .first()
    )

    if conversation is None:
        logger.warning(
            "Access denied: conversation=%s not found or not owned by user=%s",
            conversation_id,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


def get_owned_message(
    db: Session,
    user_id: str,
    message_id: int | str,
    conversation_id: int | str | None = None,
) -> ConversationMessage:
    """Retrieve a message verifying conversation ownership and relationship integrity.

    For nested objects, validates the entire relationship:
      1. Message ID exists.
      2. Message belongs to a Conversation.
      3. Conversation belongs to the authenticated user.
      4. If conversation_id is provided, message.conversation_id must match.

    Raises:
        HTTPException(404): If message is missing, unowned, or relationship is mismatched.
    """
    try:
        msg_id = int(message_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    query = (
        db.query(ConversationMessage)
        .join(Conversation, ConversationMessage.conversation_id == Conversation.id)
        .filter(
            ConversationMessage.id == msg_id,
            Conversation.user_id == user_id,
        )
    )

    if conversation_id is not None:
        try:
            expected_conv_id = int(conversation_id)
            query = query.filter(ConversationMessage.conversation_id == expected_conv_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

    message = query.first()
    if message is None:
        logger.warning(
            "Access denied: message=%s not found or relationship invalid for user=%s",
            message_id,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return message


def get_owned_feedback(
    db: Session,
    user_id: str,
    message_id: int | str,
) -> AnswerFeedback:
    """Retrieve feedback record ensuring message and feedback ownership for user.

    Raises:
        HTTPException(404): If feedback or message does not belong to user.
    """
    # 1. Enforce message ownership first
    get_owned_message(db, user_id=user_id, message_id=message_id)

    # 2. Retrieve feedback record
    try:
        msg_id = int(message_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this message.",
        )

    feedback = (
        db.query(AnswerFeedback)
        .filter(
            AnswerFeedback.message_id == msg_id,
            AnswerFeedback.user_id == user_id,
        )
        .first()
    )

    if feedback is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this message.",
        )

    return feedback
