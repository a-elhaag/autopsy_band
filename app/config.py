"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""

    app_url: str = "http://localhost:8000"
    app_name: str = "Autopsy Band"

    model_annotator: str = "anthropic/claude-3.5-sonnet"
    model_verifier: str = "anthropic/claude-3.5-sonnet"
    model_scorer: str = "anthropic/claude-3.5-sonnet"
    model_reconstructor: str = "anthropic/claude-3.5-sonnet"
    model_apex: str = "anthropic/claude-3.5-sonnet"
    model_escalation: str = "anthropic/claude-3.5-sonnet"

    max_input_chars: int = 5000

    # --- Band transport (optional; in-process orchestrator is the fallback) ---
    band_enabled: bool = False
    band_chat_id: str = ""
    band_initiator_api_key: str = ""
    band_timeout: float = 120.0


settings = Settings()
