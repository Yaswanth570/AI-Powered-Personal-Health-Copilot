"""API routes for document intelligence.

Exposes endpoints for:
- PDF selectable-text extraction (``/extract-text``).
- OCR text extraction for images and scanned PDFs (``/extract-text-ocr``).
- Gemini AI structured clinical extraction (``/analyze-ai``).

Files are read into memory and never persisted. Document contents are never
logged.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse

from ..config import get_settings
from ..schemas import (
    AnalyzeDocumentError,
    AnalyzeDocumentRequest,
    MedicalDocumentExtraction,
    OcrTextExtractionResponse,
    PageText,
    PdfTextExtractionError,
    PdfTextExtractionResponse,
)
from ..services.gemini_extractor import (
    GeminiApiError,
    GeminiConfigError,
    GeminiExtractionError,
    GeminiInputError,
    GeminiInvalidOutputError,
    GeminiRateLimitError,
    extract_medical_document,
)
from ..services.ocr_service import OcrUnavailableError, ocr_image_bytes, ocr_scanned_pdf
from ..services.pdf_extractor import PdfExtractionError, extract_text_from_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}
ALLOWED_EXTENSIONS = {".pdf"}

# File types accepted by the OCR endpoint.
OCR_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
OCR_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/octet-stream",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


def _has_pdf_extension(filename: str | None) -> bool:
    if not filename:
        return False
    return filename.lower().endswith(".pdf")


def _has_ocr_extension(filename: str | None) -> bool:
    if not filename:
        return False
    name = filename.lower()
    return any(name.endswith(ext) for ext in OCR_ALLOWED_EXTENSIONS)


def _detect_file_kind(file_bytes: bytes, filename: str | None) -> Literal["pdf", "image", None]:
    """Detect the actual file kind from magic bytes (content, not extension).

    Returns ``"pdf"``, ``"image"`` (JPEG/PNG), or ``None`` if unrecognized.
    The filename is accepted for API symmetry but is not trusted for type
    detection.
    """

    # PDF: the %PDF- header should appear within the first 1024 bytes
    # (some valid PDFs have leading whitespace/bytes before the header).
    head = file_bytes[:1024]
    if b"%PDF-" in head:
        return "pdf"
    # JPEG: FF D8 FF
    if len(file_bytes) >= 3 and file_bytes[:3] == b"\xff\xd8\xff":
        return "image"
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if len(file_bytes) >= 8 and file_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"
    return None


@router.post(
    "/extract-text",
    response_model=PdfTextExtractionResponse,
    responses={
        400: {"model": PdfTextExtractionError},
        413: {"model": PdfTextExtractionError},
        415: {"model": PdfTextExtractionError},
        422: {"model": PdfTextExtractionError},
    },
    summary="Extract text from a PDF",
    description=(
        "Accepts a single PDF file (up to 10 MB), extracts selectable text "
        "page-by-page using PyMuPDF, and returns the text. No OCR is "
        "performed; image-only PDFs will report no selectable text."
    ),
)
async def extract_pdf_text(file: UploadFile = File(...)) -> PdfTextExtractionResponse:
    settings = get_settings()

    # Validate the file name and content type before reading the body.
    if not _has_pdf_extension(file.filename):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content=PdfTextExtractionError(
                error="unsupported_file_type",
                message="Only PDF files are supported. Please upload a .pdf file.",
            ).model_dump(),
        )

    # Read the entire file into memory (10 MB cap enforced below).
    file_bytes = await file.read()

    if len(file_bytes) > settings.max_upload_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=PdfTextExtractionError(
                error="file_too_large",
                message=(
                    f"The file exceeds the 10 MB limit "
                    f"({len(file_bytes) / (1024 * 1024):.1f} MB). "
                    "Please compress or split the PDF and try again."
                ),
            ).model_dump(),
        )

    if len(file_bytes) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=PdfTextExtractionError(
                error="empty_document",
                message="The uploaded file is empty and cannot be processed.",
            ).model_dump(),
        )

    try:
        result = extract_text_from_pdf(file_bytes)
    except PdfExtractionError as exc:
        status_code = _status_for_error(exc.code)
        return JSONResponse(
            status_code=status_code,
            content=PdfTextExtractionError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )

    note = (
        "Text was extracted from selectable PDF content. No OCR was performed."
        if result.has_selectable_text
        else (
            "No selectable text was found. This PDF may contain scanned images "
            "or images without a text layer. OCR support is planned for a "
            "future milestone; no fabricated text has been returned."
        )
    )

    pages = [
        PageText(
            page_number=page.page_number,
            text=page.text,
            char_count=page.char_count,
        )
        for page in result.pages
    ]

    return PdfTextExtractionResponse(
        page_count=result.page_count,
        pages=pages,
        full_text=result.full_text,
        total_char_count=result.total_char_count,
        has_selectable_text=result.has_selectable_text,
        note=note,
    )


def _status_for_error(code: str) -> int:
    return {
        "invalid_pdf": status.HTTP_400_BAD_REQUEST,
        "encrypted_pdf": status.HTTP_400_BAD_REQUEST,
        "empty_document": status.HTTP_400_BAD_REQUEST,
        "no_text_extracted": status.HTTP_200_OK,
        "extraction_failed": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "ocr_unavailable": status.HTTP_503_SERVICE_UNAVAILABLE,
        "too_many_pages": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    }.get(code, status.HTTP_400_BAD_REQUEST)


@router.post(
    "/extract-text-ocr",
    response_model=OcrTextExtractionResponse,
    responses={
        400: {"model": PdfTextExtractionError},
        413: {"model": PdfTextExtractionError},
        415: {"model": PdfTextExtractionError},
        422: {"model": PdfTextExtractionError},
        503: {"model": PdfTextExtractionError},
    },
    summary="Extract text with OCR from an image or scanned PDF",
    description=(
        "Accepts a PDF, JPG, JPEG, or PNG file (up to 10 MB). For PDFs with a "
        "selectable text layer, that text is returned directly. For scanned "
        "PDFs and images, Tesseract OCR is used. Pages are processed in memory."
    ),
)
async def extract_text_with_ocr(
    file: UploadFile = File(...),
) -> OcrTextExtractionResponse | JSONResponse:
    settings = get_settings()

    # Validate filename extension before reading the body.
    if not _has_ocr_extension(file.filename):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content=PdfTextExtractionError(
                error="unsupported_file_type",
                message=(
                    "Only PDF, JPG, JPEG, and PNG files are supported for OCR."
                ),
            ).model_dump(),
        )

    file_bytes = await file.read()

    if len(file_bytes) > settings.max_upload_bytes:
        return JSONResponse(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            content=PdfTextExtractionError(
                error="file_too_large",
                message=(
                    f"The file exceeds the 10 MB limit "
                    f"({len(file_bytes) / (1024 * 1024):.1f} MB). "
                    "Please compress or split the file and try again."
                ),
            ).model_dump(),
        )

    if len(file_bytes) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=PdfTextExtractionError(
                error="empty_document",
                message="The uploaded file is empty and cannot be processed.",
            ).model_dump(),
        )

    file_kind = _detect_file_kind(file_bytes, file.filename)
    if file_kind is None:
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content=PdfTextExtractionError(
                error="unsupported_file_type",
                message=(
                    "The file content does not look like a PDF, JPEG, or PNG. "
                    "Please upload a supported file type."
                ),
            ).model_dump(),
        )

    pages: list[PageText] = []
    ocr_engine = "tesseract"
    ocr_languages: list[str] = []
    has_text = False
    note = ""

    try:
        if file_kind == "pdf":
            # First, try the fast selectable-text path. Only fall back to OCR
            # if no selectable text is found.
            try:
                result = extract_text_from_pdf(file_bytes)
            except PdfExtractionError as exc:
                status_code = _status_for_error(exc.code)
                return JSONResponse(
                    status_code=status_code,
                    content=PdfTextExtractionError(
                        error=exc.code,
                        message=exc.message,
                    ).model_dump(),
                )

            if result.has_selectable_text:
                pages = [
                    PageText(
                        page_number=p.page_number,
                        text=p.text,
                        char_count=p.char_count,
                        method="selectable",
                    )
                    for p in result.pages
                ]
                ocr_engine = "none (PDF text layer)"
                ocr_languages = []
                has_text = True
                note = (
                    "Text was extracted from the PDF's selectable text layer. "
                    "OCR was not needed. No AI interpretation was performed."
                )
            else:
                # No selectable text: render pages and OCR them.
                ocr_result = ocr_scanned_pdf(
                    file_bytes,
                    languages=list(settings.ocr_languages),
                    dpi=settings.ocr_dpi,
                    max_pages=settings.ocr_max_pages,
                )
                pages = [
                    PageText(
                        page_number=p.page_number,
                        text=p.text,
                        char_count=p.char_count,
                        method="ocr",
                    )
                    for p in ocr_result.pages
                ]
                ocr_engine = ocr_result.ocr_engine
                ocr_languages = ocr_result.languages
                has_text = ocr_result.has_text
                note = (
                    "This PDF had no selectable text layer, so pages were "
                    "rendered and recognized with Tesseract OCR. OCR output "
                    "is raw and may contain errors; it has not been "
                    "interpreted by AI. Tesseract may perform poorly on "
                    "handwritten text."
                )
        else:
            # Image file: OCR directly.
            ocr_result = ocr_image_bytes(
                file_bytes,
                languages=list(settings.ocr_languages),
            )
            pages = [
                PageText(
                    page_number=p.page_number,
                    text=p.text,
                    char_count=p.char_count,
                    method="ocr",
                )
                for p in ocr_result.pages
            ]
            ocr_engine = ocr_result.ocr_engine
            ocr_languages = ocr_result.languages
            has_text = ocr_result.has_text
            note = (
                "Text was recognized from the image with Tesseract OCR. "
                "OCR output is raw and may contain errors; it has not been "
                "interpreted by AI. Tesseract may perform poorly on "
                "handwritten text."
            )
    except OcrUnavailableError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=PdfTextExtractionError(
                error="ocr_unavailable",
                message=str(exc),
            ).model_dump(),
        )
    except ValueError as exc:
        # Map service-level value errors (invalid image, too many pages, etc.)
        # to appropriate HTTP responses.
        message = str(exc)
        if "maximum" in message and "pages" in message:
            code = "too_many_pages"
            http_status = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        elif "encrypted" in message:
            code = "encrypted_pdf"
            http_status = status.HTTP_400_BAD_REQUEST
        elif "no pages" in message:
            code = "empty_document"
            http_status = status.HTTP_400_BAD_REQUEST
        else:
            code = "invalid_pdf"
            http_status = status.HTTP_400_BAD_REQUEST
        return JSONResponse(
            status_code=http_status,
            content=PdfTextExtractionError(error=code, message=message).model_dump(),
        )

    if not has_text:
        note = (
            "OCR completed but no text was detected. The image may be blank, "
            "too low-resolution, or contain only handwriting that Tesseract "
            "could not recognize. No text was fabricated."
        )

    full_text = "\n".join(p.text for p in pages)
    total_char_count = sum(p.char_count for p in pages)

    return OcrTextExtractionResponse(
        page_count=len(pages),
        pages=pages,
        full_text=full_text,
        total_char_count=total_char_count,
        has_text=has_text,
        ocr_engine=ocr_engine,
        ocr_languages=ocr_languages,
        note=note,
    )


@router.post(
    "/analyze-ai",
    response_model=MedicalDocumentExtraction,
    responses={
        400: {"model": AnalyzeDocumentError},
        413: {"model": AnalyzeDocumentError},
        429: {"model": AnalyzeDocumentError},
        502: {"model": AnalyzeDocumentError},
        503: {"model": AnalyzeDocumentError},
    },
    summary="Extract structured medical information using Gemini AI",
    description=(
        "Accepts extracted document text (from selectable PDF or OCR) and uses Gemini "
        "to produce structured clinical entities with Pydantic validation. Enforces "
        "strict fidelity to the source without hallucination or inferred diagnoses."
    ),
)
async def analyze_document_with_ai(
    payload: AnalyzeDocumentRequest,
) -> MedicalDocumentExtraction | JSONResponse:
    try:
        extraction = extract_medical_document(
            text=payload.text,
            pages=payload.pages,
            document_type_hint=payload.document_type_hint,
        )
        return extraction
    except GeminiConfigError as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=AnalyzeDocumentError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )
    except GeminiInputError as exc:
        http_status = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if exc.code == "text_too_large"
            else status.HTTP_400_BAD_REQUEST
        )
        return JSONResponse(
            status_code=http_status,
            content=AnalyzeDocumentError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )
    except GeminiRateLimitError as exc:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=AnalyzeDocumentError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )
    except GeminiInvalidOutputError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=AnalyzeDocumentError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )
    except GeminiApiError as exc:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=AnalyzeDocumentError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )
    except GeminiExtractionError as exc:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=AnalyzeDocumentError(
                error=exc.code,
                message=exc.message,
            ).model_dump(),
        )
