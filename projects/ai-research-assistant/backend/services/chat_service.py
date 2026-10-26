"""Chat Service coordinating conversation state, query rewriting, retrieval, and generation."""

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.services.conversation_service import (
    MAX_HISTORY_MESSAGES,
    ConversationService,
    default_conversation_service,
)
from backend.services.observability import measure_stage
from backend.services.query_rewriter import QueryRewriter
from backend.services.query_router import classify_query
from backend.services.rag_service import run_rag_pipeline

logger = logging.getLogger(__name__)


class ChatService:
    """Orchestrates conversational RAG execution across conversation and retrieval layers."""

    def __init__(
        self,
        conversation_service: ConversationService | None = None,
        query_rewriter: QueryRewriter | None = None,
        query_router: Any | None = None,
        retriever: Any | None = None,
        reranker: Any | None = None,
        generator: Any | None = None,
        rag_service: Any | None = None,
        llm: Any | None = None,
    ):
        self.conversation_service = conversation_service or default_conversation_service
        self.query_rewriter = query_rewriter or QueryRewriter(llm=llm)
        self.query_router = query_router or classify_query
        self.retriever = retriever
        self.reranker = reranker
        self.generator = generator
        self.rag_service = rag_service
        self.llm = llm

    def chat(
        self,
        db: Session,
        user_id: str,
        message: str,
        conversation_id: int | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
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
        metrics: dict[str, Any] = {}
        with measure_stage("query_rewriting", metrics):
            rewritten_query = self.query_rewriter.rewrite(clean_msg, history)
        logger.info("Original: '%s' -> Standalone: '%s'", clean_msg, rewritten_query)

        # 4. Execute retrieval and answer generation
        try:
            if self.rag_service is not None and hasattr(self.rag_service, "run_rag_pipeline"):
                rag_res = self.rag_service.run_rag_pipeline(
                    query=clean_msg,
                    filename=filename,
                    user_id=user_id,
                    db=db,
                    conversation_id=conversation_id,
                    conversation_history=history,
                    persist_messages=False,
                    metrics=metrics
                )
            elif callable(self.rag_service):
                rag_res = self.rag_service(
                    query=clean_msg,
                    filename=filename,
                    user_id=user_id,
                    db=db,
                    conversation_id=conversation_id,
                    conversation_history=history,
                    persist_messages=False,
                    metrics=metrics
                )
            else:
                rag_res = run_rag_pipeline(
                    query=clean_msg,
                    filename=filename,
                    user_id=user_id,
                    db=db,
                    conversation_id=conversation_id,
                    conversation_history=history,
                    persist_messages=False,
                    metrics=metrics
                )
        except TypeError:
            # Fallback if custom rag_service doesn't accept metrics keyword argument
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

        if isinstance(rag_res, dict) and "metrics" in rag_res:
            metrics.update(rag_res["metrics"])

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
        assistant_msg = self.conversation_service.add_message(
            db,
            conversation_id=conversation_id,
            role="assistant",
            content=answer
        )

        # 6. Build structured response
        return {
            "conversation_id": conversation_id,
            "message_id": assistant_msg.id if assistant_msg else None,
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
            "latency_ms": rag_res.get("latency_ms", 0.0),
            "metrics": metrics
        }

    def process_chat(
        self,
        query: str,
        history: list[Any] | None = None,
    ) -> dict[str, Any]:
        """Process chat through pipeline stages with stage-level timing metrics."""
        metrics: dict[str, Any] = {}

        with measure_stage("query_rewriting", metrics):
            rewritten_query = self.query_rewriter.rewrite(
                query,
                history or [],
            )

        with measure_stage("retrieval", metrics):
            if self.retriever and hasattr(self.retriever, "retrieve"):
                chunks = self.retriever.retrieve(rewritten_query)
            elif callable(self.retriever):
                chunks = self.retriever(rewritten_query)
            else:
                chunks = []
        metrics["candidate_count"] = len(chunks)
        metrics["empty_retrieval"] = len(chunks) == 0

        with measure_stage("reranking", metrics):
            if self.reranker and hasattr(self.reranker, "rerank"):
                ranked_chunks = self.reranker.rerank(
                    rewritten_query,
                    chunks,
                    top_k=5,
                )
            elif callable(self.reranker):
                ranked_chunks = self.reranker(
                    rewritten_query,
                    chunks,
                    top_k=5,
                )
            else:
                ranked_chunks = chunks[:5]
        metrics["reranked_count"] = len(ranked_chunks)

        with measure_stage("generation", metrics):
            if self.generator and hasattr(self.generator, "generate"):
                answer = self.generator.generate(ranked_chunks)
            elif callable(self.generator):
                answer = self.generator(ranked_chunks)
            elif self.llm:
                answer = str(self.llm(ranked_chunks))
            else:
                answer = "Answer based on context."
        metrics["generation_outcome"] = "success"

        return {
            "answer": answer,
            "metrics": metrics,
        }

    async def async_chat(
        self,
        db: Session,
        user_id: str,
        message: str,
        conversation_id: int | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """Execute chat request asynchronously via worker thread without blocking the event loop."""
        import asyncio
        return await asyncio.to_thread(
            self.chat,
            db=db,
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
            filename=filename,
        )


default_chat_service = ChatService()
