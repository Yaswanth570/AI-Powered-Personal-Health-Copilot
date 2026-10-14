"""Document-processing services."""

from .gemini_extractor import (
    GeminiApiError,
    GeminiConfigError,
    GeminiExtractionError,
    GeminiInputError,
    GeminiInvalidOutputError,
    GeminiRateLimitError,
    extract_medical_document,
)
from .ocr_service import OcrUnavailableError, ocr_image_bytes, ocr_scanned_pdf
from .pdf_extractor import PdfExtractionError, extract_text_from_pdf

__all__ = [
    "extract_medical_document",
    "GeminiExtractionError",
    "GeminiConfigError",
    "GeminiInputError",
    "GeminiRateLimitError",
    "GeminiInvalidOutputError",
    "GeminiApiError",
    "extract_text_from_pdf",
    "PdfExtractionError",
    "ocr_image_bytes",
    "ocr_scanned_pdf",
    "OcrUnavailableError",
]
