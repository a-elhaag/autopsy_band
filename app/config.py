"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""

    app_url: str = "http://localhost:8000"
    app_name: str = "Autopsy Band"

    model_annotator: str = "nex-agi/nex-n2-pro:free"   # broad classify, agentic MoE (verified)
    model_verifier: str = "openai/gpt-oss-120b"         # precision, verified strong
    model_scorer: str = "openai/gpt-oss-20b"            # fast structured JSON (verified)
    model_reconstructor: str = "openai/gpt-oss-120b"    # spec writing, strong (verified)
    model_apex: str = "openai/gpt-oss-120b"             # synthesis, verified strong
    model_escalation: str = "openai/gpt-oss-20b"        # binary decision, fast (verified)

    max_input_chars: int = 5000

    # --- Band transport (optional; in-process orchestrator is the fallback) ---
    band_enabled: bool = False
    band_chat_id: str = ""
    band_initiator_api_key: str = ""
    band_timeout: float = 120.0


settings = Settings()
