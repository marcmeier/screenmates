from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All configuration comes from the environment or `backend/.env`."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_name: str = "screenmates"
    database_url: str = f"sqlite:///{BASE_DIR / 'screenmates.db'}"

    # TMDB — leave empty to run on seed data only.
    tmdb_api_key: str = ""
    tmdb_language: str = "de-DE"
    tmdb_region: str = "DE"
    tmdb_image_base: str = "https://image.tmdb.org/t/p"
    tmdb_timeout: float = 10.0

    # LLM for the "KI-Suche" feature — optional. Two API styles:
    #   anthropic  : Anthropic Messages API
    #   openrouter : OpenAI-compatible chat completions (OpenRouter, or any such API via LLM_BASE_URL)
    # Empty provider: guessed from the key (OpenRouter keys start with "sk-or-").
    # Empty base URL / model: the provider's default in LLM_DEFAULTS.
    llm_provider: Literal["", "anthropic", "openrouter"] = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    # Kino (live screen sharing) via MediaMTX. Empty URL disables the feature.
    mediamtx_webrtc_url: str = ""  # e.g. http://127.0.0.1:8889
    mediamtx_api_url: str = "http://127.0.0.1:9997"

    # Uploaded files (profile pictures). Empty: backend/media. Docker: /data/media.
    media_dir: str = ""

    session_cookie: str = "screenmates_sid"
    # Set to true when served over HTTPS so the session cookie is never sent in clear.
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173"

    @property
    def media_path(self) -> Path:
        return Path(self.media_dir) if self.media_dir else BASE_DIR / "media"

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key)

    @property
    def kino_enabled(self) -> bool:
        return bool(self.mediamtx_webrtc_url)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def llm_backend(self) -> str:
        if self.llm_provider:
            return self.llm_provider
        return "openrouter" if self.llm_api_key.startswith("sk-or-") else "anthropic"

    @property
    def llm_url(self) -> str:
        return (self.llm_base_url or LLM_DEFAULTS[self.llm_backend][0]).rstrip("/")

    @property
    def llm_model_name(self) -> str:
        return self.llm_model or LLM_DEFAULTS[self.llm_backend][1]


# Base URL and model per LLM provider, used when LLM_BASE_URL / LLM_MODEL are empty.
# OpenRouter defaults to an inexpensive model: every proposed title is checked against
# TMDB anyway, so the KI-Suche needs film knowledge, not a frontier model.
LLM_DEFAULTS = {
    "anthropic": ("https://api.anthropic.com/v1", "claude-opus-5-5"),
    "openrouter": ("https://openrouter.ai/api/v1", "deepseek/deepseek-v4.1-flash"),
}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
