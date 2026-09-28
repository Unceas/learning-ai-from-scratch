"""Conversations API route handling conversation memory and query rewriting endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.schemas.conversations import (
    ConversationCreate,
    ConversationMessageCreate,
    ConversationResponse,
    ConversationMessagesPageResponse,
    ConversationChatResponse,
)
from backend.services.conversation_service import (
    create_conversation,
    get_conversation,
    list_conversations,
    delete_conversation,
    get_paginated_messages,
)
from backend.services.chat_service import default_chat_service

router = APIRouter()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_new_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Create a new conversation for the authenticated user."""
    conv = create_conversation(db, user_id=user_id, title=payload.title)
    return conv


@router.get("", response_model=List[ConversationResponse], include_in_schema=False)
@router.get("/", response_model=List[ConversationResponse])
def get_user_conversations(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """List all conversations belonging to the authenticated user."""
    return list_conversations(db, user_id=user_id, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation_details(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve an authenticated user's conversation by ID.
    
    Enforces multi-tenant isolation: accessing another user's conversation yields 404.
    """
    conv = get_conversation(db, user_id=user_id, conversation_id=conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )
    return conv


@router.delete("/{conversation_id}")
def delete_user_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Delete an authenticated user's conversation.
    
    Enforces multi-tenant isolation: deleting another user's conversation yields 404.
    Cascades to delete conversation messages while leaving documents intact.
    """
    deleted = delete_conversation(db, user_id=user_id, conversation_id=conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )
    return {"status": "deleted", "conversation_id": conversation_id}


@router.get("/{conversation_id}/messages", response_model=ConversationMessagesPageResponse)
def get_conversation_messages_paginated(
    conversation_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve paginated messages for an authenticated user's conversation.
    
    Enforces multi-tenant isolation: accessing another user's messages yields 404.
    """
    page_data = get_paginated_messages(
        db,
        user_id=user_id,
        conversation_id=conversation_id,
        limit=limit,
        offset=offset
    )
    if page_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )
    return page_data


@router.post("/{conversation_id}/messages", response_model=ConversationChatResponse)
def send_conversation_message(
    conversation_id: int,
    payload: ConversationMessageCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Send a message to a conversation.
    
    Orchestrates query rewriting, RAG retrieval, answer generation, and message
    persistence via ChatService.
    """
    try:
        result = default_chat_service.chat(
            db=db,
            user_id=user_id,
            message=payload.message,
            conversation_id=conversation_id,
            filename=payload.filename
        )

        return ConversationChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            query=result.get("query", {
                "original": payload.message,
                "rewritten": result.get("rewritten_query", payload.message)
            }),
            conversation_id=conversation_id,
            citation_map=result.get("citation_map"),
            invalid_citations=result.get("invalid_citations", []),
            subqueries=result.get("subqueries", []),
            expanded_queries=result.get("expanded_queries", []),
            used_hyde=result.get("used_hyde", False),
            user_id=user_id
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversational RAG execution failed: {str(exc)}"
        ) from exc
