"""Centralized application configuration settings using Pydantic Settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "AI Research Assistant"
    app_version: str = "1.0.0"

    environment: str = "development"

    chroma_path: str = "./document_db"
    memory_path: str = "./memory_db"

    embedding_model: str = "all-MiniLM-L6-v2"

    max_upload_size_mb: int = 20

    storage_type: str = "local"
    storage_path: str = "uploads"

    jwt_secret_key: str = "change-this-development-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Two-stage retrieval, reranking, and multi-query configuration
    rag_candidate_k: int = 20
    rag_final_k: int = 5
    reranker_enabled: bool = True
    reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    query_routing_enabled: bool = True
    multi_query_enabled: bool = True
    max_subqueries: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
