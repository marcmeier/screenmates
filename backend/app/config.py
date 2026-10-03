from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_name: str = "screenmates"
    database_url: str = f"sqlite:///{BASE_DIR / 'screenmates.db'}"

    # TMDB — leave empty to run on seed data only.
    tmdb_api_key: str = ""
    tmdb_language: str = "de-DE"
    tmdb_region: str = "DE"
    tmdb_image_base: str = "https://image.tmdb.org/t/p"

    # LLM for the "KI-Suche" feature — optional.
    llm_api_key: str = ""
    llm_base_url: str = "https://api.anthropic.com/v1"
    llm_model: str = "claude-opus-4-8"

    # Where cut video clips live.
    media_dir: str = str(BASE_DIR / "media")

    session_cookie: str = "screenmates_sid"
    cors_origins: str = "http://localhost:5173"

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
