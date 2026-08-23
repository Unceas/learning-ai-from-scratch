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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
