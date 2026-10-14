"""FastAPI application entry point for the document-intelligence backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat_routes import router as chat_router
from .api.persistence_routes import router as persistence_router
from .api.routes import router as documents_router
from .config import get_settings
from .db.init_db import init_database

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: initialize database schema and ensure seed records exist."""
    try:
        init_database()
        logger.info("Database schema initialized and verified.")
    except Exception as exc:
        logger.warning("Database initialization deferred or failed: %s", exc)
    yield


app = FastAPI(
    title="Personal Health Copilot — Document Intelligence API",
    version="0.1.0",
    description=(
        "Personal Health Copilot API for medical document intelligence: "
        "extract selectable text from PDFs, OCR for scanned documents and images, "
        "Gemini AI structured clinical extraction, and PostgreSQL persistence."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok", "service": "document-intelligence"}


app.include_router(documents_router)
app.include_router(persistence_router)
app.include_router(chat_router)

