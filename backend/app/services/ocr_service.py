"""OCR service using Tesseract via pytesseract.

This module wraps Tesseract OCR for image documents and scanned PDF pages.
It is intentionally decoupled from HTTP concerns: callers pass raw bytes or
a PIL image and receive structured text.

Design notes:
- Tesseract availability is detected at import time. If the executable or
  its language data is missing, :class:`OcrUnavailableError` is raised on
  use so the API layer can return a useful setup error instead of crashing.
- PDF pages are rendered to in-memory PNG images with PyMuPDF before OCR.
- No document contents are logged and no files are written to disk.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

try:  # pragma: no cover - import availability depends on the environment
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None  # type: ignore[assignment]

try:  # pragma: no cover
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]


class OcrUnavailableError(Exception):
    """Raised when Tesseract (or its language data) cannot be used.

    The message explains how to install Tesseract so callers can surface a
    useful setup error to the user.
    """


@dataclass(frozen=True)
class OcrPageResult:
    """OCR result for a single page/image."""

    page_number: int
    text: str
    method: str = "ocr"

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class OcrResult:
    """Structured OCR result for one document (one or more pages)."""

    page_count: int
    pages: list[OcrPageResult]
    ocr_engine: str
    languages: list[str]
    has_text: bool

    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def total_char_count(self) -> int:
        return sum(page.char_count for page in self.pages)


def _tesseract_cmd() -> str | None:
    """Return the path to the Tesseract executable, or None if missing."""

    if pytesseract is None:
        return None
    configured = getattr(pytesseract.pytesseract, "tesseract_cmd", None)
    if configured and isinstance(configured, str) and Path(configured).exists():
        return configured
    found = shutil.which("tesseract")
    if found:
        return found
    # Common Windows install locations (UB-Mannheim installer).
    for candidate in (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def get_available_languages() -> list[str]:
    """Return the list of Tesseract language codes installed.

    Raises :class:`OcrUnavailableError` if Tesseract is not installed.
    """

    tesseract = _tesseract_cmd()
    if tesseract is None or pytesseract is None:
        raise OcrUnavailableError(
            "Tesseract OCR is not installed. Install Tesseract "
            "(e.g. `winget install UB-Mannheim.TesseractOCR` on Windows) and "
            "ensure the `tesseract` command is on PATH, then restart the "
            "backend."
        )
    # Point pytesseract at the discovered executable.
    pytesseract.pytesseract.tesseract_cmd = tesseract
    try:
        langs = pytesseract.get_languages(config="")
    except Exception as exc:  # noqa: BLE001
        raise OcrUnavailableError(
            "Tesseract is installed but its language data could not be read. "
            "Verify that `tessdata` language files are present and that the "
            "`tesseract --list-langs` command works."
        ) from exc
    return sorted(langs)


def _resolve_languages(requested: list[str] | None) -> list[str]:
    """Resolve the OCR language list.

    If ``requested`` is empty/None, default to ``eng``. Validate each
    requested language against the installed set and raise
    :class:`OcrUnavailableError` for any missing language.
    """

    installed = get_available_languages()
    if not requested:
        requested = ["eng"]
    missing = [lang for lang in requested if lang not in installed]
    if missing:
        raise OcrUnavailableError(
            f"OCR language(s) not installed: {', '.join(missing)}. "
            f"Installed languages: {', '.join(installed)}."
        )
    return requested


def _ocr_image(image: "Image.Image", languages: list[str]) -> str:
    """Run Tesseract on a PIL image and return normalized text."""

    if pytesseract is None:
        raise OcrUnavailableError(
            "The `pytesseract` Python package is not installed. Run "
            "`pip install pytesseract` and ensure Tesseract is available."
        )
    lang = "+".join(languages)
    text = pytesseract.image_to_string(image, lang=lang) or ""
    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def ocr_image_bytes(image_bytes: bytes, languages: list[str] | None = None) -> OcrResult:
    """OCR a single image (JPEG/PNG) from raw bytes.

    Args:
        image_bytes: Raw bytes of a JPEG or PNG image.
        languages: Optional list of Tesseract language codes. Defaults to
            ``["eng"]``.

    Returns:
        An :class:`OcrResult` with a single page.
    """

    if Image is None:
        raise OcrUnavailableError(
            "The Pillow package is not installed. Run `pip install Pillow`."
        )
    resolved_languages = _resolve_languages(languages)

    import io

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("The file is not a valid image and could not be opened.") from exc

    text = _ocr_image(image, resolved_languages)
    page = OcrPageResult(page_number=1, text=text, method="ocr")
    return OcrResult(
        page_count=1,
        pages=[page],
        ocr_engine="tesseract",
        languages=resolved_languages,
        has_text=bool(text.strip()),
    )


def ocr_scanned_pdf(
    pdf_bytes: bytes,
    languages: list[str] | None = None,
    dpi: int = 200,
    max_pages: int = 20,
) -> OcrResult:
    """OCR a scanned (image-only) PDF.

    Each page is rendered to an in-memory image at ``dpi`` resolution and
    passed to Tesseract. Pages are not written to disk.

    Args:
        pdf_bytes: Raw bytes of a PDF file.
        languages: Optional list of Tesseract language codes.
        dpi: Rendering DPI for each page. Capped to prevent resource abuse.
        max_pages: Maximum number of pages to OCR.

    Returns:
        An :class:`OcrResult` with one entry per processed page.

    Raises:
        OcrUnavailableError: If Tesseract is unavailable or a requested
            language is missing.
        ValueError: If the file is not a valid PDF or exceeds ``max_pages``.
    """

    if Image is None:
        raise OcrUnavailableError(
            "The Pillow package is not installed. Run `pip install Pillow`."
        )

    resolved_languages = _resolve_languages(languages)
    safe_dpi = min(max(dpi, 72), 400)

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except (fitz.FileDataError, fitz.EmptyFileError) as exc:
        raise ValueError("The file is not a valid PDF and could not be opened.") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError("The file could not be opened as a PDF.") from exc

    try:
        if document.needs_pass:
            raise ValueError("This PDF is encrypted or password-protected and cannot be processed.")
        page_count = document.page_count
        if page_count == 0:
            raise ValueError("The PDF contains no pages.")
        if page_count > max_pages:
            raise ValueError(
                f"This PDF has {page_count} pages, which exceeds the maximum "
                f"of {max_pages} pages for OCR. Please split the PDF."
            )

        import io

        pages: list[OcrPageResult] = []
        for index in range(page_count):
            page = document.load_page(index)
            pix = page.get_pixmap(dpi=safe_dpi)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = _ocr_image(image, resolved_languages)
            pages.append(OcrPageResult(page_number=index + 1, text=text, method="ocr"))
    finally:
        document.close()

    has_text = any(page.text.strip() for page in pages)
    return OcrResult(
        page_count=page_count,
        pages=pages,
        ocr_engine="tesseract",
        languages=resolved_languages,
        has_text=has_text,
    )
