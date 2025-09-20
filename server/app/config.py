from functools import lru_cache
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    server_port: int = 8000
    # Allow both localhost and 127.0.0.1 for local development
    allowed_origins: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]  # type: ignore
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    deepseek_api_key: Optional[str] = None
    # OpenRouter config
    openrouter_api_key: Optional[str] = None
    openrouter_http_referer: Optional[str] = None
    openrouter_app_title: Optional[str] = None

    # pydantic-settings v2 style config: load env from both ../.env (repo root) and .env
    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=("../.env", ".env"),
        extra="ignore",  # ignore env vars not defined as fields
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


