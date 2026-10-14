"""Tests for Telugu Health Summary and Clinical Explanation Service (Step 7).

Validates:
- Patient-friendly Telugu explanation generation using mocked Gemini API.
- Strict preservation of medicine names, doses, units, and laboratory values.
- Presence of Telugu script (U+0C00–U+0C7F) in explanations.
- Proper medical safety disclaimer in Telugu.
- Error handling: missing API key (503), rate limit (429), API/model error (502), validation errors.
"""

from __future__ import annotations

import json
from typing import Generator
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from google.genai import errors
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.models import (
    DiagnosisRecord,
    LabResultRecord,
    MedicalDocument,
    MedicationRecord,
    Patient,
)
from app.db.session import get_db
from app.main import app
from app.schemas import (
    DiagnosisItem,
    LabTestItem,
    MedicalDocumentExtraction,
    MedicationItem,
    TeluguHealthSummary,
)

FICTIONAL_EXTRACTION = MedicalDocumentExtraction(
    document_type="Prescription",
    report_date="2026-10-12",
    patient_name="Smt. Kamala Devi",
    patient_age="58",
    patient_gender="Female",
    diagnoses=[
        DiagnosisItem(
            diagnosis="Type 2 Diabetes Mellitus",
            status="chronic",
            evidence="1. Type 2 Diabetes Mellitus (Uncontrolled)",
            page_number=1,
        ),
        DiagnosisItem(
            diagnosis="Essential Hypertension",
            status="active",
            evidence="2. Essential Hypertension (Stage 1)",
            page_number=1,
        ),
    ],
    medicines=[
        MedicationItem(
            name="Tab. Metformin HCl",
            dose="500 mg",
            frequency="1-0-1",
            duration="30 days",
            route="oral",
            instructions="after food",
            evidence="Tab. Metformin HCl 500 mg 1-0-1 after food",
            page_number=1,
        ),
        MedicationItem(
            name="Tab. Telmisartan",
            dose="40 mg",
            frequency="1-0-0",
            duration="30 days",
            route="oral",
            instructions="morning",
            evidence="Tab. Telmisartan 40 mg OD",
            page_number=1,
        ),
    ],
    lab_tests=[
        LabTestItem(
            test_name="Fasting Blood Sugar",
            value="142",
            unit="mg/dL",
            reference_range="70 - 100 mg/dL",
            abnormal_flag=True,
            evidence="Fasting Blood Sugar (FBS): 142 mg/dL (HIGH)",
            page_number=1,
        ),
        LabTestItem(
            test_name="HbA1c",
            value="7.4",
            unit="%",
            reference_range="< 5.7 %",
            abnormal_flag=True,
            evidence="HbA1c: 7.4 % (ABNORMAL)",
            page_number=1,
        ),
    ],
    missing_fields=[],
    uncertainties=[],
    confidence="high",
    summary="Outpatient consultation for uncontrolled Type 2 Diabetes and Hypertension.",
    disclaimer="AI-extracted medical information.",
    model_used="gemini-3.1-flash-lite",
)

MOCK_TELUGU_RESPONSE = {
    "overall_summary_telugu": "ఈ ప్రిస్క్రిప్షన్ ప్రకారం రోగికి మధుమేహం (Type 2 Diabetes Mellitus) మరియు రక్తపోటు (Hypertension) నియంత్రణ కొరకు ఔషధాలు సూచించబడ్డాయి.",
    "diagnoses_explanations": [
        {
            "original_diagnosis": "Type 2 Diabetes Mellitus",
            "telugu_explanation": "రక్తంలో చక్కెర స్థాయి ఎక్కువగా ఉండే దీర్ఘకాలిక మధుమేహ వ్యాధి (Type 2 Diabetes). ఆహార నియమాలు మరియు మందులతో దీనిని నియంత్రించవచ్చు.",
            "status": "chronic",
            "evidence": "1. Type 2 Diabetes Mellitus (Uncontrolled)",
        },
        {
            "original_diagnosis": "Essential Hypertension",
            "telugu_explanation": "అధిక రక్తపోటు (High Blood Pressure). గుండె ఆరోగ్యాన్ని కాపాడటానికి క్రమం తప్పకుండా మందులు వాడాలి.",
            "status": "active",
            "evidence": "2. Essential Hypertension (Stage 1)",
        },
    ],
    "medicines_explanations": [
        {
            "name": "Tab. Metformin HCl",
            "dose": "500 mg",
            "frequency": "1-0-1",
            "duration": "30 days",
            "instructions": "after food",
            "telugu_purpose_and_instructions": "రక్తంలో చక్కెర శాతాన్ని అదుపులో ఉంచడానికి వాడే మాత్ర (Tab. Metformin HCl 500 mg). భోజనం తర్వాత ఉదయం మరియు రాత్రి (1-0-1) 30 రోజుల పాటు తీసుకోవాలి.",
        },
        {
            "name": "Tab. Telmisartan",
            "dose": "40 mg",
            "frequency": "1-0-0",
            "duration": "30 days",
            "instructions": "morning",
            "telugu_purpose_and_instructions": "రక్తపోటును అదుపులో ఉంచడానికి వాడే మాత్ర (Tab. Telmisartan 40 mg). ఉదయం ఒకసారి (1-0-0) 30 రోజుల పాటు తీసుకోవాలి.",
        },
    ],
    "labs_explanations": [
        {
            "test_name": "Fasting Blood Sugar",
            "value": "142",
            "unit": "mg/dL",
            "reference_range": "70 - 100 mg/dL",
            "abnormal_flag": True,
            "telugu_explanation": "పరగడుపున చేసిన రక్త పరీక్షలో చక్కెర శాతం 142 mg/dL గా ఉంది (సాధారణ స్థాయి: 70 - 100 mg/dL). ఇది సాధారణం కంటే ఎక్కువగా ఉంది.",
        },
        {
            "test_name": "HbA1c",
            "value": "7.4",
            "unit": "%",
            "reference_range": "< 5.7 %",
            "abnormal_flag": True,
            "telugu_explanation": "గత 3 నెలల సగటు చక్కెర స్థాయి 7.4 % గా నమోదైంది (సాధారణ స్థాయి: 5.7 % కన్నా తక్కువ). ఇది మధుమేహం అదుపులో లేదని సూచిస్తుంది.",
        },
    ],
    "disclaimer_telugu": "ఈ సమాచారం కేవలం రోగి అవగాహన కొరకు మాత్రమే. ఇది వైద్య నిర్ధారణ లేదా చికిత్స సలహా కాదు. ఎల్లప్పుడూ మీ వైద్యుడిని సంప్రదించండి.",
    "model_used": "gemini-3.1-flash-lite",
}


def _mock_settings(gemini_key: str = "test-fake-key-12345") -> Settings:
    return Settings(
        gemini_api_key=gemini_key,
        gemini_model="gemini-3.1-flash-lite",
        database_url="sqlite:///:memory:",
    )


def test_explain_telugu_successful() -> None:
    """Test generating a structured Telugu explanation from clinical extraction."""
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_TELUGU_RESPONSE, ensure_ascii=False)
    mock_genai_client.models.generate_content.return_value = mock_response

    with patch("app.services.telugu_explainer.genai.Client", return_value=mock_genai_client), \
         patch("app.services.telugu_explainer.get_settings", return_value=_mock_settings()):
        with TestClient(app) as client:
            res = client.post(
                "/api/documents/explain-telugu",
                json={"extraction": FICTIONAL_EXTRACTION.model_dump()},
            )

    assert res.status_code == 200, res.text
    data = res.json()

    # Validate overall summary
    assert "మధుమేహం" in data["overall_summary_telugu"]
    assert len(data["diagnoses_explanations"]) == 2
    assert len(data["medicines_explanations"]) == 2
    assert len(data["labs_explanations"]) == 2

    # Validate clinical value preservation
    med1 = data["medicines_explanations"][0]
    assert med1["name"] == "Tab. Metformin HCl"
    assert med1["dose"] == "500 mg"
    assert med1["frequency"] == "1-0-1"
    assert med1["duration"] == "30 days"
    # Telugu explanation must contain Telugu characters
    assert any("\u0c00" <= c <= "\u0c7f" for c in med1["telugu_purpose_and_instructions"])

    lab1 = data["labs_explanations"][0]
    assert lab1["test_name"] == "Fasting Blood Sugar"
    assert lab1["value"] == "142"
    assert lab1["unit"] == "mg/dL"
    assert lab1["abnormal_flag"] is True

    # Validate disclaimer in Telugu
    assert "వైద్య నిర్ధారణ లేదా చికిత్స సలహా కాదు" in data["disclaimer_telugu"]


def test_explain_telugu_missing_api_key_returns_503() -> None:
    """If GEMINI_API_KEY is not set, the endpoint returns HTTP 503."""
    with patch("app.services.telugu_explainer.get_settings", return_value=_mock_settings(gemini_key="")):
        with TestClient(app) as client:
            res = client.post(
                "/api/documents/explain-telugu",
                json={"extraction": FICTIONAL_EXTRACTION.model_dump()},
            )
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


def test_explain_telugu_rate_limit_returns_429() -> None:
    """If Gemini rate limit is reached, returns HTTP 429."""
    mock_genai_client = MagicMock()
    mock_api_error = errors.APIError(429, "Resource has been exhausted (e.g. check quota).")
    mock_genai_client.models.generate_content.side_effect = mock_api_error

    with patch("app.services.telugu_explainer.genai.Client", return_value=mock_genai_client), \
         patch("app.services.telugu_explainer.get_settings", return_value=_mock_settings()):
        with TestClient(app) as client:
            res = client.post(
                "/api/documents/explain-telugu",
                json={"extraction": FICTIONAL_EXTRACTION.model_dump()},
            )
    assert res.status_code == 429
    assert "rate limit or quota exceeded" in res.json()["detail"].lower()


def test_explain_telugu_malformed_output_returns_502() -> None:
    """If Gemini returns unparseable text, returns HTTP 502."""
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Invalid JSON {{{ broken text"
    mock_genai_client.models.generate_content.return_value = mock_response

    with patch("app.services.telugu_explainer.genai.Client", return_value=mock_genai_client), \
         patch("app.services.telugu_explainer.get_settings", return_value=_mock_settings()):
        with TestClient(app) as client:
            res = client.post(
                "/api/documents/explain-telugu",
                json={"extraction": FICTIONAL_EXTRACTION.model_dump()},
            )
    assert res.status_code == 502
    assert "could not be validated" in res.json()["detail"].lower()


def test_explain_telugu_missing_payload_returns_400() -> None:
    """Sending an empty extraction returns HTTP 400."""
    with TestClient(app) as client:
        res = client.post(
            "/api/documents/explain-telugu",
            json={"extraction": None},
        )
    assert res.status_code == 400
    assert "required" in res.json()["detail"].lower()


def test_explain_telugu_empty_extraction_fields() -> None:
    """Test generating a summary when extraction contains empty clinical fields."""
    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "overall_summary_telugu": "ఈ పత్రంలో ఎటువంటి రోగనిర్ధారణలు లేదా మందుల వివరాలు పేర్కొనబడలేదు.",
        "diagnoses_explanations": [],
        "medicines_explanations": [],
        "labs_explanations": [],
        "disclaimer_telugu": "ఈ సమాచారం కేవలం రోగి అవగాహన కొరకు మాత్రమే.",
        "model_used": "gemini-3.1-flash-lite",
    }, ensure_ascii=False)
    mock_genai_client.models.generate_content.return_value = mock_response

    empty_extraction = MedicalDocumentExtraction(
        document_type="Lab Report",
        report_date=None,
        patient_name=None,
        diagnoses=[],
        medications=[],
        lab_results=[],
    )

    with patch("app.services.telugu_explainer.genai.Client", return_value=mock_genai_client), \
         patch("app.services.telugu_explainer.get_settings", return_value=_mock_settings()):
        with TestClient(app) as client:
            res = client.post(
                "/api/documents/explain-telugu",
                json={"extraction": empty_extraction.model_dump()},
            )

    assert res.status_code == 200
    data = res.json()
    assert data["diagnoses_explanations"] == []
    assert data["medicines_explanations"] == []
    assert data["labs_explanations"] == []
    assert "overall_summary_telugu" in data


def test_explain_persisted_document_telugu_success() -> None:
    """Test generating Telugu summary from a persisted database document."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine)

    def _override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db

    # Seed patient, document, and clinical records
    with TestingSessionLocal() as db:
        patient = Patient(display_name="Smt. Kamala Devi", age="58", gender="Female")
        db.add(patient)
        db.flush()

        doc = MedicalDocument(
            patient_id=patient.id,
            filename="kamala_devi_prescription.pdf",
            document_type="Prescription",
            upload_date="2026-10-12",
            raw_text="Sample prescription text",
        )
        db.add(doc)
        db.flush()

        diag = DiagnosisRecord(
            document_id=doc.id,
            patient_id=patient.id,
            diagnosis="Type 2 Diabetes Mellitus",
            status="chronic",
            evidence="1. Type 2 Diabetes Mellitus (Uncontrolled)",
        )
        med = MedicationRecord(
            document_id=doc.id,
            patient_id=patient.id,
            name="Tab. Metformin HCl",
            dose="500 mg",
            frequency="1-0-1",
            duration="30 days",
            instructions="After food",
        )
        db.add_all([diag, med])
        db.commit()
        doc_id = str(doc.id)

    mock_genai_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(MOCK_TELUGU_RESPONSE, ensure_ascii=False)
    mock_genai_client.models.generate_content.return_value = mock_response

    try:
        with patch("app.services.telugu_explainer.genai.Client", return_value=mock_genai_client), \
             patch("app.services.telugu_explainer.get_settings", return_value=_mock_settings()):
            with TestClient(app) as client:
                res = client.get(f"/api/documents/{doc_id}/explain-telugu")

        assert res.status_code == 200, res.text
        data = res.json()
        assert "మధుమేహం" in data["overall_summary_telugu"]
        assert len(data["diagnoses_explanations"]) == 2
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)


def test_explain_persisted_document_not_found() -> None:
    """Requesting Telugu explanation for a non-existent document returns 404."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(bind=test_engine)

    def _override_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    random_doc_id = str(uuid.uuid4())
    try:
        with TestClient(app) as client:
            res = client.get(f"/api/documents/{random_doc_id}/explain-telugu")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)

