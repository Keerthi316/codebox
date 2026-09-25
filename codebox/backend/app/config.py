from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CodeBox"
    database_url: str = "postgresql+psycopg://codebox:codebox@postgres:5432/codebox"
    redis_url: str = "redis://redis:6379/0"

    # No default on purpose: the app refuses to start without a real secret.
    jwt_secret: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # AI assistant. OpenRouter is used when OPENROUTER_API_KEY is set; otherwise any
    # OpenAI-compatible Chat Completions endpoint configured via OPENAI_*.
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen3.8-27b:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    public_url: str = "http://localhost:8080"  # sent to OpenRouter for app attribution
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    ai_timeout: float = 45.0

    # Registration checks that the email's domain can receive mail (DNS/MX lookup).
    email_check_deliverability: bool = True

    # Sandbox limits (read by the worker's executor; exposed via /languages)
    execution_timeout: float = 2.0
    memory_limit: str = "128m"
    cpu_limit: float = 0.5

    # Abuse protection
    max_source_bytes: int = 64 * 1024
    max_stdin_bytes: int = 64 * 1024
    max_pending_executions_per_user: int = 3
    rate_limit_login_per_minute: int = 10
    rate_limit_executions_per_minute: int = 30
    rate_limit_ai_per_minute: int = 10
    stale_execution_seconds: int = 300

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8080"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
