"""Tests for the PDF text extraction endpoint.

Covers:
- A valid text-bearing PDF extracts text page-by-page.
- An image-only (no text layer) PDF returns no selectable text and no OCR claim.
- An invalid (non-PDF) file returns a clear error.
- An upload larger than 10 MB is rejected.
- An empty file is rejected.
"""

from __future__ import annotations

import io

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

from app.main import app


def _make_text_pdf(text: str = "Sample medical report\nHemoglobin: 13.8 g/dL") -> bytes:
    """Create a single-page PDF with selectable text."""
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 700), text)
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


def _make_image_only_pdf() -> bytes:
    """Create a single-page PDF containing only an image (no text layer)."""
    document = fitz.open()
    page = document.new_page()
    # Draw a solid rectangle as a stand-in image; no text is inserted.
    page.draw_rect(fitz.Rect(50, 50, 400, 400), color=(0, 0, 0), fill=(0.8, 0.8, 0.8))
    buffer = io.BytesIO()
    document.save(buffer)
    document.close()
    return buffer.getvalue()


from typing import Generator

from app.api.auth_routes import get_current_user
from app.db.models import User

_TEST_USER = User(
    id="test-user-pdf",
    email="pdf-tester@example.com",
    hashed_password="pw",
    full_name="PDF Tester",
    is_active=True,
)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_current_user] = lambda: _TEST_USER
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_current_user, None)


def test_valid_text_pdf_extracts_text(client: TestClient) -> None:
    pdf_bytes = _make_text_pdf()
    files = {"file": ("report.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/api/documents/extract-text", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["page_count"] == 1
    assert body["has_selectable_text"] is True
    assert body["total_char_count"] > 0
    assert "Hemoglobin" in body["full_text"]
    assert len(body["pages"]) == 1
    assert body["pages"][0]["page_number"] == 1
    assert "Hemoglobin" in body["pages"][0]["text"]
    assert "OCR was performed" in body["note"]


def test_image_only_pdf_returns_no_text_and_no_ocr_claim(client: TestClient) -> None:
    pdf_bytes = _make_image_only_pdf()
    files = {"file": ("scan.pdf", pdf_bytes, "application/pdf")}

    response = client.post("/api/documents/extract-text", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["has_selectable_text"] is False
    assert body["total_char_count"] == 0
    assert body["full_text"] == ""
    # Must not claim OCR occurred or return fabricated text.
    assert "OCR support is planned" in body["note"]
    assert "no fabricated text" in body["note"]


def test_invalid_pdf_returns_error(client: TestClient) -> None:
    files = {"file": ("not-a-pdf.pdf", b"this is definitely not a pdf", "application/pdf")}

    response = client.post("/api/documents/extract-text", files=files)

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "invalid_pdf"
    assert "not a valid PDF" in body["message"]


def test_empty_file_returns_error(client: TestClient) -> None:
    files = {"file": ("empty.pdf", b"", "application/pdf")}

    response = client.post("/api/documents/extract-text", files=files)

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "empty_document"


def test_unsupported_extension_returns_error(client: TestClient) -> None:
    files = {"file": ("notes.txt", b"hello", "text/plain")}

    response = client.post("/api/documents/extract-text", files=files)

    assert response.status_code == 415
    body = response.json()
    assert body["error"] == "unsupported_file_type"


def test_oversized_file_is_rejected(client: TestClient) -> None:
    # The 10 MB size check runs before PyMuPDF, so arbitrary bytes over the
    # limit with a .pdf extension are enough to exercise it.
    oversized = b"x" * (11 * 1024 * 1024)

    files = {"file": ("huge.pdf", oversized, "application/pdf")}
    response = client.post("/api/documents/extract-text", files=files)

    assert response.status_code == 413
    body = response.json()
    assert body["error"] == "file_too_large"
    assert "10 MB" in body["message"]


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
