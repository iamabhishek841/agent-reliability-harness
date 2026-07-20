from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local .env."""

    app_env: str = "development"
    log_level: str = "INFO"
    legacy_database_url: str = "postgresql://legacy:legacy@localhost:5433/legacy_crm"
    knowledge_database_url: str = "postgresql://knowledge:knowledge@localhost:5434/knowledge_platform"
    llm_provider: Literal["ollama", "groq", "rules"] = "ollama"
    llm_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    groq_api_key: str | None = None
    api_auth_token: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    llm_input_cost_per_million_usd: float = Field(default=0.0, ge=0.0)
    llm_output_cost_per_million_usd: float = Field(default=0.0, ge=0.0)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    integration_timeout_seconds: float = Field(default=4.0, gt=0.0)
    chaos_state_path: str = "chaos/state.json"
    otel_service_name: str = "agent-reliability-backend"
    otel_exporter_otlp_endpoint: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

