"""Application configuration loaded from environment variables.

No secrets are required for this milestone. The API base URL and allowed
origins are configurable so the frontend can point at a local backend.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env if present, followed by any default .env
_backend_env = Path(__file__).resolve().parent.parent / ".env"
if _backend_env.is_file():
    load_dotenv(_backend_env)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the document-intelligence backend."""

    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    )
    # OCR safety limits.
    ocr_max_pages: int = 20
    ocr_dpi: int = 200
    ocr_languages: tuple[str, ...] = ("eng",)

    # Gemini AI configuration.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.1-flash-lite"
    max_ai_text_chars: int = 150_000

    # PostgreSQL Database configuration.
    database_url: str | None = None

    # CORS configuration
    cors_origin_regex: str | None = None


def _parse_origins(raw: str) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in raw.split(",") if origin.strip())


def get_settings() -> Settings:
    """Build settings, allowing environment overrides.

    ``MAX_UPLOAD_BYTES`` overrides the 10 MB limit.
    ``CORS_ORIGINS`` is a comma-separated list of allowed origins.
    ``CORS_ORIGIN_REGEX`` is a regex pattern matching allowed origins (e.g. Vercel preview deploys).
    ``GEMINI_API_KEY`` provides the Google Gen AI API key.
    ``GEMINI_MODEL`` overrides the Gemini model name (default: gemini-3.1-flash-lite).
    ``MAX_AI_TEXT_CHARS`` overrides the max characters for AI extraction.
    ``DATABASE_URL`` provides the PostgreSQL connection string.
    """

    raw_max = os.getenv("MAX_UPLOAD_BYTES")
    max_bytes = int(raw_max) if raw_max and raw_max.isdigit() else Settings.max_upload_bytes

    raw_origins = os.getenv("CORS_ORIGINS")
    if raw_origins:
        parsed_custom = _parse_origins(raw_origins)
        # Combine custom origins with local development origins for seamless testing
        origins = tuple(dict.fromkeys(parsed_custom + Settings.allowed_origins))
    else:
        origins = Settings.allowed_origins

    raw_origin_regex = os.getenv("CORS_ORIGIN_REGEX")
    cors_origin_regex = (
        raw_origin_regex.strip()
        if raw_origin_regex and raw_origin_regex.strip()
        else None
    )

    raw_pages = os.getenv("OCR_MAX_PAGES")
    ocr_max_pages = (
        int(raw_pages) if raw_pages and raw_pages.isdigit() else Settings.ocr_max_pages
    )

    raw_dpi = os.getenv("OCR_DPI")
    ocr_dpi = int(raw_dpi) if raw_dpi and raw_dpi.isdigit() else Settings.ocr_dpi

    raw_langs = os.getenv("OCR_LANGUAGES")
    ocr_languages = (
        tuple(lang.strip() for lang in raw_langs.split(",") if lang.strip())
        if raw_langs
        else Settings.ocr_languages
    )

    raw_gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_api_key = (
        raw_gemini_key.strip()
        if raw_gemini_key and raw_gemini_key.strip()
        else None
    )

    raw_gemini_model = os.getenv("GEMINI_MODEL")
    gemini_model = (
        raw_gemini_model.strip()
        if raw_gemini_model and raw_gemini_model.strip()
        else Settings.gemini_model
    )

    raw_max_ai_chars = os.getenv("MAX_AI_TEXT_CHARS")
    max_ai_text_chars = (
        int(raw_max_ai_chars)
        if raw_max_ai_chars and raw_max_ai_chars.isdigit()
        else Settings.max_ai_text_chars
    )

    raw_db_url = os.getenv("DATABASE_URL")
    database_url = raw_db_url.strip() if raw_db_url and raw_db_url.strip() else None

    return Settings(
        max_upload_bytes=max_bytes,
        allowed_origins=origins,
        cors_origin_regex=cors_origin_regex,
        ocr_max_pages=ocr_max_pages,
        ocr_dpi=ocr_dpi,
        ocr_languages=ocr_languages,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        max_ai_text_chars=max_ai_text_chars,
        database_url=database_url,
    )
