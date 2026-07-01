"""
Configuration management for the Deep Research Agent Platform.

Uses pydantic-settings to load from environment variables and .env file.
Priority: env vars > .env file > defaults.
"""

from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine .env path: look in project root (../.env) and backend/.env
_ENV_FILE = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if not _ENV_FILE.exists():
    _ENV_FILE = Path(".env")  # fallback to cwd

# Explicitly load all .env vars into os.environ (for non-Settings fields like API keys)
load_dotenv(_ENV_FILE, override=True)


class Settings(BaseSettings):
    """Application settings loaded from .env and environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./data/research.db"

    # ── Vector Store ─────────────────────────────────────────────────
    VECTOR_STORE_TYPE: Literal["faiss", "milvus", "qdrant", "chroma", "mock"] = "faiss"

    # ── Search API ───────────────────────────────────────────────────
    SEARCH_API_TYPE: Literal["mock", "serper", "tavily", "brave", "serpapi"] = "mock"

    # ── Financial Data API ───────────────────────────────────────────
    FINANCIAL_API_TYPE: Literal["mock", "tushare", "akshare", "yfinance", "none"] = "mock"

    # ── Export ───────────────────────────────────────────────────────
    EXPORT_DIR: str = "./data/exports"

    # ── Agent / Research ─────────────────────────────────────────────
    MAX_ITERATIONS: int = 3

    # ── Server ───────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # ── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Sandbox ──────────────────────────────────────────────────────
    SANDBOX_DIR: str = "./data/sandbox"
    ALLOWED_IMPORTS: str = "math,statistics,json,csv,datetime,collections,itertools,functools,re,typing,dataclasses,copy,textwrap,string,decimal,fractions,random,numpy,pandas,matplotlib"

    def get_allowed_imports(self) -> list[str]:
        """Return ALLOWED_IMPORTS as a list."""
        return [m.strip() for m in self.ALLOWED_IMPORTS.split(",") if m.strip()]


# ── Singleton ─────────────────────────────────────────────────────────────

_settings: Settings | None = None


def get_settings() -> Settings:
    """Return cached Settings, creating on first call."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
