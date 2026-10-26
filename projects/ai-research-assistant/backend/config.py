"""Centralized application configuration settings using Pydantic Settings."""

from functools import lru_cache
from typing import Any, Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application & Environment
    app_name: str = "AI Research Assistant"
    app_version: str = "1.0.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    # Database & Storage
    database_url: str = "sqlite:///./app.db"
    storage_type: Literal["local", "s3"] = "local"
    storage_path: str = "uploads"
    chroma_path: str = "./document_db"
    memory_path: str = "./memory_db"
    max_upload_size_mb: int = 20

    # AI Models
    embedding_model: str = "all-MiniLM-L6-v2"
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        validation_alias=AliasChoices(
            "reranker_model", "reranker_model_name", "RERANKER_MODEL", "RERANKER_MODEL_NAME"
        ),
    )
    llm_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("llm_model", "LLM_MODEL"),
    )

    # Secrets
    llm_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "llm_api_key", "LLM_API_KEY", "gemini_api_key", "GEMINI_API_KEY"
        ),
    )
    jwt_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("jwt_secret_key", "JWT_SECRET_KEY"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Timeouts & Concurrency
    llm_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        le=300,
        validation_alias=AliasChoices(
            "llm_timeout_seconds",
            "llm_request_timeout_seconds",
            "LLM_TIMEOUT_SECONDS",
            "LLM_REQUEST_TIMEOUT_SECONDS",
        ),
    )
    max_llm_concurrency: int = Field(
        default=8,
        ge=1,
        le=100,
        validation_alias=AliasChoices(
            "max_llm_concurrency",
            "max_concurrent_llm_requests",
            "MAX_LLM_CONCURRENCY",
            "MAX_CONCURRENT_LLM_REQUESTS",
        ),
    )
    max_concurrent_ingestions: int = 2
    max_concurrent_retrieval_workers: int = 4
    retrieval_timeout_seconds: float = 15.0

    # Cache Capacities
    embedding_cache_entries: int = Field(
        default=512,
        ge=1,
        validation_alias=AliasChoices(
            "embedding_cache_entries", "embedding_cache_size", "EMBEDDING_CACHE_ENTRIES"
        ),
    )
    retrieval_cache_entries: int = Field(
        default=256,
        ge=1,
        validation_alias=AliasChoices(
            "retrieval_cache_entries", "retrieval_cache_size", "RETRIEVAL_CACHE_ENTRIES"
        ),
    )

    # RAG Pipeline Configuration
    rag_candidate_k: int = 20
    rag_final_k: int = 5
    reranker_enabled: bool = True
    query_routing_enabled: bool = True
    multi_query_enabled: bool = True
    max_subqueries: int = 4
    hybrid_retrieval_enabled: bool = True
    bm25_enabled: bool = True
    rrf_k: int = 60
    query_expansion_enabled: bool = True
    max_expanded_queries: int = 2
    hyde_enabled: bool = True
    query_rewriting_enabled: bool = True
    max_history_messages: int = 10

    # CORS Origins
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
        ]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def reranker_model_name(self) -> str:
        return self.reranker_model

    @property
    def max_concurrent_llm_requests(self) -> int:
        return self.max_llm_concurrency

    @property
    def llm_request_timeout_seconds(self) -> float:
        return self.llm_timeout_seconds

    @property
    def embedding_cache_size(self) -> int:
        return self.embedding_cache_entries

    @property
    def raw_jwt_secret(self) -> str:
        if self.jwt_secret_key is not None:
            return self.jwt_secret_key.get_secret_value()
        return "change-this-development-secret"

    @model_validator(mode="after")
    def validate_environment(self):
        if self.environment == "production":
            if self.debug:
                raise ValueError("Debug mode must be disabled in production")

            if not self.jwt_secret_key:
                raise ValueError(
                    "JWT_SECRET_KEY is required in production"
                )

            if not self.llm_api_key:
                raise ValueError(
                    "LLM_API_KEY is required in production"
                )

            if self.storage_type == "local":
                raise ValueError(
                    "Configure production storage explicitly"
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
