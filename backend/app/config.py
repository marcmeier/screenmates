from functools import lru_cache
from pathlib import Path

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

    # LLM for the "KI-Suche" feature — optional, Anthropic Messages API.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.anthropic.com/v1"
    llm_model: str = "claude-opus-5-5"

    # Kino (live screen sharing) via MediaMTX. Empty URL disables the feature.
    mediamtx_webrtc_url: str = ""  # e.g. http://127.0.0.1:8889
    mediamtx_api_url: str = "http://127.0.0.1:9997"

    session_cookie: str = "screenmates_sid"
    # Set to true when served over HTTPS so the session cookie is never sent in clear.
    cookie_secure: bool = False
    cors_origins: str = "http://localhost:5173"

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key)

    @property
    def kino_enabled(self) -> bool:
        return bool(self.mediamtx_webrtc_url)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
