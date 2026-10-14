"""PDF text extraction using PyMuPDF.

This module contains the document-processing logic. It intentionally has no
knowledge of HTTP, request validation, or response formatting: it takes raw
file bytes and returns structured extraction data.

No extracted text is logged. Uploaded files are processed in memory.
"""

from __future__ import annotations

from dataclasses import dataclass

import fitz  # PyMuPDF


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be processed.

    ``code`` maps to the error identifier returned to API clients.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PageExtraction:
    """Text extracted from a single page."""

    page_number: int
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class ExtractionResult:
    """Structured result of extracting text from a PDF."""

    page_count: int
    pages: list[PageExtraction]
    has_selectable_text: bool

    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def total_char_count(self) -> int:
        return sum(page.char_count for page in self.pages)


def extract_text_from_pdf(file_bytes: bytes) -> ExtractionResult:
    """Extract text from a PDF document.

    Args:
        file_bytes: Raw bytes of a PDF file.

    Returns:
        A structured :class:`ExtractionResult` with per-page text.

    Raises:
        PdfExtractionError: If the file is not a valid PDF, is encrypted, is
            empty (0 pages), or cannot be opened.
    """

    if not file_bytes:
        raise PdfExtractionError(
            "empty_document",
            "The uploaded file is empty and cannot be processed.",
        )

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise PdfExtractionError(
            "invalid_pdf",
            "The file is not a valid PDF and could not be opened.",
        ) from exc
    except Exception as exc:  # noqa: BLE001 - surface as a generic invalid-PDF error
        raise PdfExtractionError(
            "invalid_pdf",
            "The file could not be opened as a PDF.",
        ) from exc

    try:
        if document.needs_pass:
            raise PdfExtractionError(
                "encrypted_pdf",
                "This PDF is encrypted or password-protected and cannot be processed.",
            )

        page_count = document.page_count
        if page_count == 0:
            raise PdfExtractionError(
                "empty_document",
                "The PDF contains no pages.",
            )

        pages: list[PageExtraction] = []
        for index in range(page_count):
            page = document.load_page(index)
            text = page.get_text("text") or ""
            # Normalize line endings for consistent downstream display.
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            pages.append(PageExtraction(page_number=index + 1, text=text))

        has_text = any(page.text.strip() for page in pages)
        return ExtractionResult(
            page_count=page_count,
            pages=pages,
            has_selectable_text=has_text,
        )
    finally:
        document.close()
