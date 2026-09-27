"""Chat Service coordinating conversation state, query rewriting, retrieval, and generation."""

import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.services.conversation_service import (
    default_conversation_service,
    ConversationService,
    MAX_HISTORY_MESSAGES
)
from backend.services.query_rewriter import QueryRewriter
from backend.services.query_router import classify_query, QueryType
from backend.services.rag_service import run_rag_pipeline

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates conversational RAG execution across conversation and retrieval layers."""

    def __init__(
        self,
        conversation_service: Optional[ConversationService] = None,
        query_rewriter: Optional[QueryRewriter] = None,
        query_router: Optional[Any] = None,
        retriever: Optional[Any] = None,
        rag_service: Optional[Any] = None,
        llm: Optional[Any] = None,
    ):
        self.conversation_service = conversation_service or default_conversation_service
        self.query_rewriter = query_rewriter or QueryRewriter(llm=llm)
        self.query_router = query_router or classify_query
        self.retriever = retriever
        self.rag_service = rag_service
        self.llm = llm

    def chat(
        self,
        db: Session,
        user_id: str,
        message: str,
        conversation_id: Optional[int] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute chat request for an authenticated user.
        
        1. If conversation_id is None, automatically create a new conversation.
        2. If conversation_id is provided, verify multi-tenant ownership (404 if unauthorized).
        3. Load recent conversation history (capped at MAX_HISTORY_MESSAGES).
        4. Rewrite contextual question into a standalone research query.
        5. Execute retrieval pipeline (router -> decomposition -> expansion/HyDE -> hybrid -> reranker -> context).
        6. Persist only actual user message and assistant answer in conversation memory.
        7. Return structured chat payload.
        """
        clean_msg = message.strip() if message else ""
        if not clean_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message cannot be empty."
            )

        # 1. Resolve or create conversation
        if conversation_id is None:
            # Generate descriptive preview title
            title = clean_msg[:35] + ("..." if len(clean_msg) > 35 else "")
            conv = self.conversation_service.create_conversation(db, user_id=user_id, title=title)
            conversation_id = conv.id
            logger.info("Created new conversation id=%d for user=%s", conversation_id, user_id)
        else:
            conv = self.conversation_service.get_conversation(db, user_id=user_id, conversation_id=conversation_id)
            if not conv:
                logger.warning("Conversation %s not found for user %s", conversation_id, user_id)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found."
                )

        # 2. Load recent conversation history
        history = self.conversation_service.get_recent_messages(
            db,
            conversation_id=conversation_id,
            limit=MAX_HISTORY_MESSAGES
        )

        # 3. Rewrite query into standalone research query
        rewritten_query = self.query_rewriter.rewrite(clean_msg, history)
        logger.info("Original: '%s' -> Standalone: '%s'", clean_msg, rewritten_query)

        # 4. Execute retrieval and answer generation
        if self.rag_service is not None and hasattr(self.rag_service, "run_rag_pipeline"):
            rag_res = self.rag_service.run_rag_pipeline(
                query=clean_msg,
                filename=filename,
                user_id=user_id,
                db=db,
                conversation_id=conversation_id,
                conversation_history=history,
                persist_messages=False
            )
        elif callable(self.rag_service):
            rag_res = self.rag_service(
                query=clean_msg,
                filename=filename,
                user_id=user_id,
                db=db,
                conversation_id=conversation_id,
                conversation_history=history,
                persist_messages=False
            )
        else:
            rag_res = run_rag_pipeline(
                query=clean_msg,
                filename=filename,
                user_id=user_id,
                db=db,
                conversation_id=conversation_id,
                conversation_history=history,
                persist_messages=False
            )

        answer = rag_res.get("answer", "No answer generated.")
        sources = rag_res.get("sources", [])
        final_rewritten = rag_res.get("rewritten_query", rewritten_query)

        # 5. Persist the actual exchange to conversation memory (pure dialogue, no pipeline artifacts)
        self.conversation_service.add_message(
            db,
            conversation_id=conversation_id,
            role="user",
            content=clean_msg
        )
        self.conversation_service.add_message(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=answer
        )

        # 6. Build structured response
        return {
            "conversation_id": conversation_id,
            "answer": answer,
            "sources": sources,
            "rewritten_query": final_rewritten,
            "query": {
                "original": clean_msg,
                "rewritten": final_rewritten
            },
            "citation_map": rag_res.get("citation_map", {}),
            "invalid_citations": rag_res.get("invalid_citations", []),
            "document_sources": rag_res.get("document_sources", []),
            "subqueries": rag_res.get("subqueries", []),
            "expanded_queries": rag_res.get("expanded_queries", []),
            "used_hyde": rag_res.get("used_hyde", False),
            "query_type": rag_res.get("query_type"),
            "user_id": user_id,
            "latency_ms": rag_res.get("latency_ms", 0.0)
        }


default_chat_service = ChatService()
