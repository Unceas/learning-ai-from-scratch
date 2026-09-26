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
    ConversationChatResponse,
)
from backend.services.conversation_service import (
    create_conversation,
    get_conversation,
    list_conversations,
    delete_conversation,
)
from backend.services.rag_service import run_rag_pipeline

router = APIRouter()


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_new_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Create a new conversation for the authenticated user."""
    conv = create_conversation(db, user_id=user_id, title=payload.title)
    return conv


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
    """
    deleted = delete_conversation(db, user_id=user_id, conversation_id=conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )
    return {"status": "deleted", "conversation_id": conversation_id}


@router.post("/{conversation_id}/messages", response_model=ConversationChatResponse)
def send_conversation_message(
    conversation_id: int,
    payload: ConversationMessageCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Send a message to a conversation.
    
    Loads recent conversation history, rewrites the query into a standalone query,
    executes RAG retrieval using the standalone query, synthesizes the answer,
    records the exchange in conversation memory, and returns the response with
    source attribution and query rewrite tracking.
    """
    conv = get_conversation(db, user_id=user_id, conversation_id=conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )

    try:
        rag_res = run_rag_pipeline(
            query=payload.message,
            filename=payload.filename,
            user_id=user_id,
            db=db,
            conversation_id=conversation_id
        )

        return ConversationChatResponse(
            answer=rag_res["answer"],
            sources=rag_res.get("sources", []),
            query=rag_res.get("query", {
                "original": payload.message,
                "rewritten": rag_res.get("rewritten_query", payload.message)
            }),
            conversation_id=conversation_id,
            citation_map=rag_res.get("citation_map"),
            invalid_citations=rag_res.get("invalid_citations", []),
            subqueries=rag_res.get("subqueries", []),
            expanded_queries=rag_res.get("expanded_queries", []),
            used_hyde=rag_res.get("used_hyde", False),
            user_id=user_id
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversational RAG execution failed: {str(exc)}"
        ) from exc
