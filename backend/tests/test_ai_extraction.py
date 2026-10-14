"""Tests for Gemini AI medical document extraction endpoint (/api/documents/analyze-ai).

Uses fictional Indian sample documents and mocks for all Gemini API calls:
- No real API key required.
- Zero patient data used.
- Validates structured extraction, safety rules, missing fields, rate limits, and error handling.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from google.genai import errors

from app.config import Settings
from app.main import app
from app.schemas import MedicalDocumentExtraction

# Fictional Indian clinical document text (synthetic sample for testing).
FICTIONAL_INDIAN_PRESCRIPTION_TEXT = """
APOLLO CLINIC — HYDERABAD
Consultant: Dr. Arvind Swaminathan, MD (Gen Med), Reg No: TS-48291
Date: 12-Oct-2026

Patient Name: Smt. Kamala Devi
Age: 58 Yrs / Female
UHID: HYD-2026-99482

CLINICAL IMPRESSION:
1. Type 2 Diabetes Mellitus (Uncontrolled)
2. Essential Hypertension (Stage 1)

LABORATORY INVESTIGATIONS (Same Day):
- Fasting Blood Sugar (FBS): 142 mg/dL [Ref: 70 - 100 mg/dL] (HIGH)
- HbA1c: 7.4 % [Ref: < 5.7 %] (ABNORMAL)
- Serum Creatinine: 0.9 mg/dL [Ref: 0.6 - 1.2 mg/dL] (Normal)
- HBsAg Rapid Card: Not detected [Ref: Negative]

Rx / MEDICATIONS PRESCRIBED:
1. Tab. Metformin HCl 500 mg — 1 tablet twice daily (1-0-1) — 30 days — Oral — Take after food.
2. Tab. Telmisartan 40 mg — 1 tablet once daily (1-0-0) — 30 days — Oral — Take morning after breakfast.

ADVICE:
Dietary modifications advised. Follow up after 1 month with repeat FBS.
"""

FICTIONAL_INDIAN_EXTRACTION_JSON = {
    "document_type": "Prescription and Clinical Summary",
    "report_date": "12-Oct-2026",
    "patient_name": "Smt. Kamala Devi",
    "patient_age": "58 Yrs",
    "patient_gender": "Female",
    "diagnoses": [
        {
            "diagnosis": "Type 2 Diabetes Mellitus",
            "status": "Uncontrolled",
            "evidence": "1. Type 2 Diabetes Mellitus (Uncontrolled)",
            "page_number": 1,
        },
        {
            "diagnosis": "Essential Hypertension",
            "status": "Stage 1",
            "evidence": "2. Essential Hypertension (Stage 1)",
            "page_number": 1,
        },
    ],
    "medicines": [
        {
            "name": "Tab. Metformin HCl",
            "dose": "500 mg",
            "frequency": "1-0-1",
            "duration": "30 days",
            "route": "Oral",
            "instructions": "Take after food",
            "evidence": "Tab. Metformin HCl 500 mg — 1 tablet twice daily (1-0-1) — 30 days — Oral — Take after food.",
            "page_number": 1,
        },
        {
            "name": "Tab. Telmisartan",
            "dose": "40 mg",
            "frequency": "1-0-0",
            "duration": "30 days",
            "route": "Oral",
            "instructions": "Take morning after breakfast",
            "evidence": "Tab. Telmisartan 40 mg — 1 tablet once daily (1-0-0) — 30 days — Oral — Take morning after breakfast.",
            "page_number": 1,
        },
    ],
    "lab_tests": [
        {
            "test_name": "Fasting Blood Sugar (FBS)",
            "value": "142",
            "unit": "mg/dL",
            "reference_range": "70 - 100 mg/dL",
            "abnormal_flag": True,
            "evidence": "Fasting Blood Sugar (FBS): 142 mg/dL [Ref: 70 - 100 mg/dL] (HIGH)",
            "page_number": 1,
        },
        {
            "test_name": "HbA1c",
            "value": "7.4",
            "unit": "%",
            "reference_range": "< 5.7 %",
            "abnormal_flag": True,
            "evidence": "HbA1c: 7.4 % [Ref: < 5.7 %] (ABNORMAL)",
            "page_number": 1,
        },
        {
            "test_name": "Serum Creatinine",
            "value": "0.9",
            "unit": "mg/dL",
            "reference_range": "0.6 - 1.2 mg/dL",
            "abnormal_flag": False,
            "evidence": "Serum Creatinine: 0.9 mg/dL [Ref: 0.6 - 1.2 mg/dL] (Normal)",
            "page_number": 1,
        },
        {
            "test_name": "HBsAg Rapid Card",
            "value": "Not detected",
            "unit": None,
            "reference_range": "Negative",
            "abnormal_flag": False,
            "evidence": "HBsAg Rapid Card: Not detected [Ref: Negative]",
            "page_number": 1,
        },
    ],
    "missing_fields": [],
    "uncertainties": [],
    "confidence": "high",
    "confidence_reason": "High-clarity printed clinical prescription from Apollo Clinic with legible dosage instructions and reference intervals.",
    "summary": "Outpatient consultation summary for Smt. Kamala Devi including confirmed diagnoses of diabetes and hypertension, prescribed oral medications, and associated blood work.",
    "disclaimer": "AI-extracted medical information. Always verify against original clinical documents. Not a medical diagnosis or clinical recommendation.",
    "model_used": "gemini-3.1-flash-lite",
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_ai_extraction_valid_fictional_indian_document(client: TestClient) -> None:
    """Test successful structured extraction from a valid fictional Indian prescription."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(FICTIONAL_INDIAN_EXTRACTION_JSON)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={
                "text": FICTIONAL_INDIAN_PRESCRIPTION_TEXT,
                "document_type_hint": "Prescription",
            },
        )

    assert response.status_code == 200
    data = response.json()

    # Verify structured fields
    assert data["patient_name"] == "Smt. Kamala Devi"
    assert data["report_date"] == "12-Oct-2026"
    assert len(data["diagnoses"]) == 2
    assert data["diagnoses"][0]["diagnosis"] == "Type 2 Diabetes Mellitus"
    assert data["diagnoses"][0]["evidence"] is not None

    # Verify medicines
    assert len(data["medicines"]) == 2
    assert data["medicines"][0]["name"] == "Tab. Metformin HCl"
    assert data["medicines"][0]["dose"] == "500 mg"
    assert data["medicines"][0]["frequency"] == "1-0-1"
    assert data["medicines"][0]["duration"] == "30 days"

    # Verify labs
    assert len(data["lab_tests"]) == 4
    fbs = next(item for item in data["lab_tests"] if "FBS" in item["test_name"])
    assert fbs["value"] == "142"
    assert fbs["abnormal_flag"] is True

    # Verify safety disclaimer
    assert "AI-extracted medical information" in data["disclaimer"]
    assert data["confidence"] == "high"


def test_ai_extraction_missing_fields_and_null_patient_name(client: TestClient) -> None:
    """Test that when a document does not mention patient name or diagnoses, they are null/empty."""
    sparse_extraction_json = {
        "document_type": "Laboratory Slip",
        "report_date": None,
        "patient_name": None,
        "patient_age": None,
        "patient_gender": None,
        "diagnoses": [],
        "medicines": [],
        "lab_tests": [
            {
                "test_name": "Hemoglobin",
                "value": "11.2",
                "unit": "g/dL",
                "reference_range": "12.0 - 15.0 g/dL",
                "abnormal_flag": True,
                "evidence": "Hb: 11.2 g/dL",
                "page_number": 1,
            }
        ],
        "missing_fields": [
            "patient_name not mentioned",
            "report_date not mentioned",
            "diagnoses not mentioned",
        ],
        "uncertainties": ["Header clipped, patient identifier missing."],
        "confidence": "medium",
        "confidence_reason": "Slip has valid lab values but lacks patient identification header.",
        "summary": "Isolated lab slip showing a hemoglobin result of 11.2 g/dL without patient metadata.",
        "disclaimer": "AI-extracted medical information. Always verify against original clinical documents.",
        "model_used": "gemini-3.1-flash-lite",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(sparse_extraction_json)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Hb: 11.2 g/dL (Ref: 12.0 - 15.0)"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["patient_name"] is None
    assert data["report_date"] is None
    assert len(data["diagnoses"]) == 0
    assert "patient_name not mentioned" in data["missing_fields"]
    assert "report_date not mentioned" in data["missing_fields"]


def test_ai_extraction_distinguish_not_mentioned_vs_not_detected(client: TestClient) -> None:
    """Test that 'Not detected' is preserved as a test result value, distinct from unmentioned fields."""
    viral_report_json = {
        "document_type": "Serology Report",
        "report_date": "14-Oct-2026",
        "patient_name": "Rohan Deshmukh",
        "patient_age": "32 Y",
        "patient_gender": "Male",
        "diagnoses": [],
        "medicines": [],
        "lab_tests": [
            {
                "test_name": "HCV Antibody",
                "value": "Not detected",
                "unit": None,
                "reference_range": "Negative / Non-reactive",
                "abnormal_flag": False,
                "evidence": "HCV Antibody: Not detected",
                "page_number": 1,
            }
        ],
        "missing_fields": ["prescriptions not mentioned"],
        "uncertainties": [],
        "confidence": "high",
        "confidence_reason": "Explicit serology report.",
        "summary": "Serology test indicates non-reactive result for HCV antibody.",
        "disclaimer": "AI-extracted medical information.",
        "model_used": "gemini-3.1-flash-lite",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(viral_report_json)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Patient: Rohan Deshmukh\nHCV Antibody: Not detected"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["lab_tests"][0]["value"] == "Not detected"
    assert data["lab_tests"][0]["abnormal_flag"] is False


def test_ai_extraction_malformed_model_output_returns_502(client: TestClient) -> None:
    """Test that malformed/non-JSON model output returns HTTP 502 with invalid_output."""
    mock_response = MagicMock()
    mock_response.text = "I am an AI and cannot process this request."

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "invalid_output"
    assert "validated" in data["message"].lower() or "schema" in data["message"].lower()


def test_ai_extraction_empty_response_text_returns_502(client: TestClient) -> None:
    """Test that empty string response returns HTTP 502."""
    mock_response = MagicMock()
    mock_response.text = "   "

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "invalid_output"


def test_ai_extraction_missing_api_key_returns_503(client: TestClient) -> None:
    """Test that missing GEMINI_API_KEY returns HTTP 503 with api_key_missing."""
    with (
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key=None)),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key=None)),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "api_key_missing"
    assert "GEMINI_API_KEY" in data["message"]


def test_ai_extraction_rate_limit_returns_429(client: TestClient) -> None:
    """Test that Gemini API rate limit or quota exceeded returns HTTP 429."""
    mock_client = MagicMock()
    # Create an APIError with 429 status code
    rate_error = errors.APIError(429, "Resource exhausted: quota exceeded")
    mock_client.models.generate_content.side_effect = rate_error

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 429
    data = response.json()
    assert data["error"] == "rate_limit_exceeded"


def test_ai_extraction_api_error_returns_502(client: TestClient) -> None:
    """Test that Gemini API generic failure returns HTTP 502."""
    mock_client = MagicMock()
    server_error = errors.APIError(500, "Internal Google service error")
    mock_client.models.generate_content.side_effect = server_error

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "api_error"


def test_ai_extraction_404_model_unavailable_returns_actionable_error(client: TestClient) -> None:
    """Test that when Gemini model is sunset/unavailable (HTTP 404), an actionable message is returned."""
    mock_client = MagicMock()
    not_found_error = errors.APIError(
        404,
        "This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash for the latest features and improvements.",
    )
    mock_client.models.generate_content.side_effect = not_found_error

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "api_error"
    assert "HTTP 404" in data["message"]
    assert "GEMINI_MODEL" in data["message"]


def test_ai_extraction_404_triggers_successful_fallback(client: TestClient) -> None:
    """Test that when primary model returns 404, fallback model is tried and succeeds."""
    mock_response = MagicMock()
    mock_response.text = json.dumps(FICTIONAL_INDIAN_EXTRACTION_JSON)

    mock_client = MagicMock()
    # First call (gemini-2.5-flash) raises 404; second call (gemini-3.1-flash-lite) succeeds
    not_found_error = errors.APIError(404, "This model is no longer available.")
    mock_client.models.generate_content.side_effect = [not_found_error, mock_response]

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key", gemini_model="gemini-2.5-flash")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key", gemini_model="gemini-2.5-flash")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": FICTIONAL_INDIAN_PRESCRIPTION_TEXT},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["patient_name"] == "Smt. Kamala Devi"
    assert data["model_used"] == "gemini-3.1-flash-lite"


def test_ai_extraction_503_high_demand_returns_actionable_error(client: TestClient) -> None:
    """Test that when all models return 503 high demand, an actionable retry message is returned."""
    mock_client = MagicMock()
    unavailable_error = errors.APIError(503, "This model is currently experiencing high demand. Spikes in demand are usually temporary.")
    mock_client.models.generate_content.side_effect = unavailable_error

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "Sample clinical report text."},
        )

    assert response.status_code == 502
    data = response.json()
    assert data["error"] == "api_error"
    assert "HTTP 503" in data["message"]
    assert "demand" in data["message"].lower() or "retry" in data["message"].lower()


def test_ai_extraction_empty_input_text_returns_400(client: TestClient) -> None:
    """Test that blank/empty document text returns HTTP 400."""
    with (
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": "   \n\t  "},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "empty_text"


def test_ai_extraction_oversized_input_text_returns_413(client: TestClient) -> None:
    """Test that text exceeding MAX_AI_TEXT_CHARS returns HTTP 413."""
    oversized_text = "Clinical note " * 15000  # ~210,000 chars

    with (
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key", max_ai_text_chars=5000)),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key", max_ai_text_chars=5000)),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={"text": oversized_text},
        )

    assert response.status_code == 413
    data = response.json()
    assert data["error"] == "text_too_large"


def test_ai_extraction_with_page_snippets(client: TestClient) -> None:
    """Test that multi-page payload preserves page numbers in extraction."""
    multi_page_extraction_json = {
        "document_type": "Multi-page Discharge Summary",
        "report_date": "10-Oct-2026",
        "patient_name": "Deepak Verma",
        "patient_age": "42 Y",
        "patient_gender": "Male",
        "diagnoses": [
            {
                "diagnosis": "Dengue Fever with Thrombocytopenia",
                "status": "Resolved",
                "evidence": "Final Diagnosis: Dengue Fever with Thrombocytopenia",
                "page_number": 2,
            }
        ],
        "medicines": [],
        "lab_tests": [
            {
                "test_name": "Platelet Count",
                "value": "110,000",
                "unit": "/cumm",
                "reference_range": "150,000 - 450,000",
                "abnormal_flag": True,
                "evidence": "Platelet Count on admission: 110,000 /cumm",
                "page_number": 1,
            }
        ],
        "missing_fields": [],
        "uncertainties": [],
        "confidence": "high",
        "confidence_reason": "Clear multi-page discharge summary.",
        "summary": "Discharge summary for Deepak Verma documenting resolution of dengue fever.",
        "disclaimer": "AI-extracted medical information.",
        "model_used": "gemini-3.1-flash-lite",
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(multi_page_extraction_json)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with (
        patch("app.services.gemini_extractor.get_gemini_client", return_value=mock_client),
        patch("app.api.routes.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
        patch("app.services.gemini_extractor.get_settings", return_value=Settings(gemini_api_key="test-mock-key")),
    ):
        response = client.post(
            "/api/documents/analyze-ai",
            json={
                "text": "Platelets: 110,000\nFinal Diagnosis: Dengue Fever",
                "pages": [
                    {"page_number": 1, "text": "Platelets on admission: 110,000", "char_count": 30, "method": "selectable"},
                    {"page_number": 2, "text": "Final Diagnosis: Dengue Fever", "char_count": 28, "method": "selectable"},
                ],
                "document_type_hint": "Discharge summary",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["lab_tests"][0]["page_number"] == 1
    assert data["diagnoses"][0]["page_number"] == 2
