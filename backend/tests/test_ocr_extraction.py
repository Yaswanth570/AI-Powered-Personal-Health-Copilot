"""Tests for the OCR text-extraction endpoint.

Covers:
- OCR on a generated image containing readable text.
- OCR on an image-only (scanned) PDF.
- A text-based PDF returns the selectable text layer without OCR.
- Unsupported and invalid files.
- Empty files.
- Oversized uploads.
- Missing Tesseract executable / unavailable language (mocked).
- Empty OCR results.
"""

from __future__ import annotations

import io

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app


def _make_text_image(text: str = "Hemoglobin 13.8 g/dL") -> bytes:
    """Create a PNG image containing readable text."""

    image = Image.new("RGB", (500, 120), color="white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 50), text, fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_blank_image() -> bytes:
    """Create a blank white PNG with no text."""

    image = Image.new("RGB", (300, 100), color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _make_image_only_pdf() -> bytes:
    """Create a single-page PDF containing only a raster image (no text layer).

    The image itself contains readable text so OCR should recover it.
    """

    image_bytes = _make_text_image("Glucose 110 mg/dL")
    document = fitz.open()
    page = document.new_page()
    # Insert the image as a full-page picture. No selectable text is added.
    page.insert_image(page.rect, stream=image_bytes)
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def _make_text_pdf(text: str = "Selectable PDF text layer") -> bytes:
    """Create a single-page PDF with a selectable text layer."""

    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 700), text)
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_ocr_on_image_returns_text(client: TestClient) -> None:
    image_bytes = _make_text_image()
    files = {"file": ("lab.png", image_bytes, "image/png")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 1
    assert body["ocr_engine"] == "tesseract"
    assert "eng" in body["ocr_languages"]
    assert body["has_text"] is True
    assert body["pages"][0]["method"] == "ocr"
    assert "Glucose" not in body["full_text"]  # image says Hemoglobin
    assert "Hemoglobin" in body["full_text"]


def test_ocr_on_image_only_pdf_returns_text(client: TestClient) -> None:
    pdf_bytes = _make_image_only_pdf()
    files = {"file": ("scan.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 1
    assert body["ocr_engine"] == "tesseract"
    assert body["pages"][0]["method"] == "ocr"
    assert body["has_text"] is True
    # OCR should recover the text from the rasterized image.
    assert "Glucose" in body["full_text"]


def test_text_pdf_uses_selectable_layer_not_ocr(client: TestClient) -> None:
    pdf_bytes = _make_text_pdf()
    files = {"file": ("report.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["has_text"] is True
    # The selectable text layer is used; OCR engine is reported as none.
    assert body["ocr_engine"] != "tesseract"
    assert body["pages"][0]["method"] == "selectable"
    assert "Selectable PDF text layer" in body["full_text"]


def test_ocr_unsupported_extension_returns_error(client: TestClient) -> None:
    files = {"file": ("notes.txt", b"hello", "text/plain")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 415
    body = response.json()
    assert body["error"] == "unsupported_file_type"


def test_ocr_invalid_file_content_returns_error(client: TestClient) -> None:
    # Valid extension but invalid content (not a real PDF/PNG/JPEG).
    files = {"file": ("fake.png", b"not an image", "image/png")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 415
    body = response.json()
    assert body["error"] == "unsupported_file_type"


def test_ocr_empty_file_returns_error(client: TestClient) -> None:
    files = {"file": ("empty.png", b"", "image/png")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "empty_document"


def test_ocr_oversized_file_is_rejected(client: TestClient) -> None:
    # Build an 11 MB payload with a valid PNG magic header so it passes the
    # extension check but exceeds the size limit.
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (11 * 1024 * 1024)

    files = {"file": ("huge.png", oversized, "image/png")}
    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 413
    body = response.json()
    assert body["error"] == "file_too_large"
    assert "10 MB" in body["message"]


def test_ocr_blank_image_returns_no_text(client: TestClient) -> None:
    image_bytes = _make_blank_image()
    files = {"file": ("blank.png", image_bytes, "image/png")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["has_text"] is False
    assert body["total_char_count"] == 0
    # The note must explain no text was detected and nothing was fabricated.
    assert "no text was detected" in body["note"].lower() or "no text" in body["note"].lower()


def test_ocr_missing_tesseract_returns_setup_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When Tesseract cannot be found, return a 503 setup error."""

    from app.services import ocr_service

    def fake_tesseract_cmd() -> str | None:
        return None

    monkeypatch.setattr(ocr_service, "_tesseract_cmd", fake_tesseract_cmd)

    image_bytes = _make_text_image()
    files = {"file": ("lab.png", image_bytes, "image/png")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "ocr_unavailable"
    assert "Tesseract" in body["message"]


def test_ocr_unavailable_language_returns_setup_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When a requested language is not installed, return a 503 setup error."""

    from app.api import routes
    from app.services import ocr_service

    def fake_get_languages() -> list[str]:
        return ["eng"]

    monkeypatch.setattr(ocr_service, "get_available_languages", fake_get_languages)

    # Force a language that is not in the (mocked) installed set. The routes
    # module imports get_settings into its own namespace, so patch it there.
    from app import config

    class FakeSettings:
        max_upload_bytes = config.Settings.max_upload_bytes
        allowed_origins = config.Settings.allowed_origins
        ocr_max_pages = config.Settings.ocr_max_pages
        ocr_dpi = config.Settings.ocr_dpi
        ocr_languages = ("eng", "fra")  # fra is not installed

    monkeypatch.setattr(routes, "get_settings", lambda: FakeSettings())

    image_bytes = _make_text_image()
    files = {"file": ("lab.png", image_bytes, "image/png")}

    response = client.post("/api/documents/extract-text-ocr", files=files)

    assert response.status_code == 503
    body = response.json()
    assert body["error"] == "ocr_unavailable"
    assert "fra" in body["message"]
