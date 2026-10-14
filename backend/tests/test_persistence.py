"""Tests for PostgreSQL/SQLite database persistence (Step 6).

Validates:
- Patient creation, retrieval, and listing with document counts.
- Transactional saving of medical documents and normalized clinical records (diagnoses, medications, lab tests).
- Transaction rollback on failure (no orphan or partial records).
- Foreign key validation and 404 handling.
- Cascade deletion of documents and linked clinical records.
- Metadata updates (PATCH).
- Complete isolation using an in-memory SQLite database.
"""

from __future__ import annotations

import uuid
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth_routes import get_current_user
from app.db.base import Base
from app.db.models import (
    DiagnosisRecord,
    LabResultRecord,
    MedicalDocument,
    MedicationRecord,
    Patient,
    User,
)
from app.db.session import get_db
from app.main import app

# Isolated in-memory SQLite engine for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

_TEST_USER_ID = "persistence-test-user-id"


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Create all tables before each test and drop them after each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield a fresh testing database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Seed test user for ownership association in persistence tests."""
    user = User(
        id=_TEST_USER_ID,
        email="persist@test.local",
        hashed_password="pw",
        full_name="Persist Tester",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(db_session: Session, test_user: User) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden get_db and get_current_user dependencies."""

    def _override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============================================================================
# Patient Tests
# ============================================================================


def test_create_and_list_patients(client: TestClient) -> None:
    """Test creating a patient and listing patients with document counts."""
    # Create patient 1 (fictional Indian demo profile)
    res1 = client.post(
        "/api/patients",
        json={"display_name": "Sri Ramesh Varma", "age": "48", "gender": "Male"},
    )
    assert res1.status_code == 201
    data1 = res1.json()
    assert data1["display_name"] == "Sri Ramesh Varma"
    assert data1["age"] == "48"
    assert data1["gender"] == "Male"
    assert data1["document_count"] == 0
    patient1_id = data1["id"]

    # Create patient 2
    res2 = client.post(
        "/api/patients",
        json={"display_name": "Smt. Sunita Rao", "age": "52", "gender": "Female"},
    )
    assert res2.status_code == 201
    data2 = res2.json()
    patient2_id = data2["id"]

    # List patients
    list_res = client.get("/api/patients")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 2
    names = [p["display_name"] for p in list_data["patients"]]
    assert "Sri Ramesh Varma" in names
    assert "Smt. Sunita Rao" in names

    # Get single patient
    get_res = client.get(f"/api/patients/{patient1_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == patient1_id
    assert get_res.json()["display_name"] == "Sri Ramesh Varma"


def test_get_patient_not_found(client: TestClient) -> None:
    """Requesting an unknown patient ID returns HTTP 404."""
    res = client.get("/api/patients/non-existent-uuid")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


# ============================================================================
# Document Persistence & Transaction Tests
# ============================================================================


def test_save_document_transactional_success(client: TestClient, db_session: Session) -> None:
    """Saving a document with structured AI extractions commits atomically."""
    # Create patient
    p_res = client.post(
        "/api/patients",
        json={"display_name": "Dr. Anand Kulkarni", "age": "60", "gender": "Male"},
    )
    patient_id = p_res.json()["id"]

    save_payload = {
        "patient_id": patient_id,
        "filename": "fictional_hyderabad_prescription.pdf",
        "document_type": "Prescription",
        "upload_date": "2026-10-14",
        "processing_status": "analyzed",
        "ai_analysis_status": "success",
        "page_count": 1,
        "total_char_count": 350,
        "extraction_method": "selectable",
        "confidence": "high",
        "summary": "Prescription for Type 2 Diabetes and Hypertension management.",
        "raw_text": "APOLLO CLINIC HYDERABAD\nDr. Arvind Swaminathan\nRx: Tab Metformin 500mg 1-0-1",
        "ai_extraction": {
            "document_type": "Prescription",
            "document_date": "2026-10-12",
            "patient_name": "Dr. Anand Kulkarni",
            "patient_age": "60",
            "patient_gender": "Male",
            "confidence": "high",
            "confidence_reason": "Clear legible prescription layout with explicit dosages.",
            "summary": "Prescription for Type 2 Diabetes and Hypertension management.",
            "diagnoses": [
                {
                    "diagnosis": "Type 2 Diabetes Mellitus",
                    "status": "chronic",
                    "evidence": "CLINICAL IMPRESSION: Type 2 Diabetes Mellitus",
                    "page_number": 1,
                },
                {
                    "diagnosis": "Essential Hypertension",
                    "status": "active",
                    "evidence": "Essential Hypertension (Stage 1)",
                    "page_number": 1,
                },
            ],
            "medicines": [
                {
                    "name": "Tab. Metformin",
                    "dose": "500 mg",
                    "frequency": "1-0-1",
                    "duration": "1 month",
                    "route": "oral",
                    "instructions": "after food",
                    "evidence": "Tab. Metformin 500 mg PO 1-0-1",
                    "page_number": 1,
                }
            ],
            "lab_tests": [
                {
                    "test_name": "Fasting Blood Sugar",
                    "value": "142",
                    "unit": "mg/dL",
                    "reference_range": "70 - 100 mg/dL",
                    "abnormal_flag": True,
                    "evidence": "Fasting Blood Sugar (FBS): 142 mg/dL (HIGH)",
                    "page_number": 1,
                }
            ],
            "allergies": [],
            "critical_flags": [],
            "follow_up": None,
        },
    }

    res = client.post("/api/documents/save", json=save_payload)
    assert res.status_code == 201, res.text
    saved = res.json()

    assert saved["patient_id"] == patient_id
    assert saved["filename"] == "fictional_hyderabad_prescription.pdf"
    assert saved["document_type"] == "Prescription"
    assert saved["diagnoses_count"] == 2
    assert saved["medications_count"] == 1
    assert saved["lab_results_count"] == 1
    assert len(saved["diagnoses"]) == 2
    assert len(saved["medications"]) == 1
    assert len(saved["lab_results"]) == 1

    doc_id = saved["id"]

    # Verify directly via database session
    db_doc = db_session.query(MedicalDocument).filter(MedicalDocument.id == doc_id).first()
    assert db_doc is not None
    assert db_doc.patient_id == patient_id
    assert len(db_doc.diagnoses) == 2
    assert len(db_doc.medications) == 1
    assert len(db_doc.lab_results) == 1

    # Verify normalized clinical fields
    diag_conditions = {d.diagnosis for d in db_doc.diagnoses}
    assert "Type 2 Diabetes Mellitus" in diag_conditions
    assert "Essential Hypertension" in diag_conditions

    med = db_doc.medications[0]
    assert med.name == "Tab. Metformin"
    assert med.dose == "500 mg"
    assert med.frequency == "1-0-1"
    assert med.duration == "1 month"

    lab = db_doc.lab_results[0]
    assert lab.test_name == "Fasting Blood Sugar"
    assert lab.value == "142"
    assert lab.unit == "mg/dL"
    assert lab.abnormal_flag is True


def test_save_document_invalid_patient_returns_404(client: TestClient) -> None:
    """Saving a document with an unknown patient ID returns HTTP 404."""
    payload = {
        "patient_id": str(uuid.uuid4()),
        "filename": "sample.pdf",
    }
    res = client.post("/api/documents/save", json=payload)
    assert res.status_code == 404
    assert "not exist" in res.json()["detail"].lower()


def test_save_document_transaction_rollback_on_failure(client: TestClient, db_session: Session) -> None:
    """If a database error occurs during save, the transaction is rolled back."""
    # Create patient
    p_res = client.post("/api/patients", json={"display_name": "Rollback Test Patient"})
    patient_id = p_res.json()["id"]

    save_payload = {
        "patient_id": patient_id,
        "filename": "failed_tx.pdf",
        "custom_diagnoses": [{"diagnosis": "Asthma"}],
    }

    # Simulate database commit error
    with patch.object(Session, "commit", side_effect=Exception("Simulated disk write failure")):
        res = client.post("/api/documents/save", json=save_payload)
        assert res.status_code == 500
        assert "Database transaction failed" in res.json()["detail"]

    # Verify no records were saved
    docs_in_db = db_session.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id).all()
    assert len(docs_in_db) == 0
    diagnoses_in_db = db_session.query(DiagnosisRecord).filter(DiagnosisRecord.patient_id == patient_id).all()
    assert len(diagnoses_in_db) == 0


def test_list_and_get_saved_documents(client: TestClient) -> None:
    """Test listing saved documents for a patient and retrieving document detail."""
    p_res = client.post("/api/patients", json={"display_name": "Smt. Lakshmi Priya"})
    patient_id = p_res.json()["id"]

    # Save document 1
    doc1_payload = {
        "patient_id": patient_id,
        "filename": "blood_test_oct2026.pdf",
        "document_type": "Lab Report",
        "custom_lab_results": [
            {"test_name": "HbA1c", "value": "7.1", "unit": "%", "reference_range": "< 5.7", "abnormal_flag": True}
        ],
    }
    res1 = client.post("/api/documents/save", json=doc1_payload)
    assert res1.status_code == 201
    doc1_id = res1.json()["id"]

    # Save document 2
    doc2_payload = {
        "patient_id": patient_id,
        "filename": "discharge_summary.pdf",
        "document_type": "Discharge Summary",
        "custom_diagnoses": [{"diagnosis": "Acute Bronchitis"}],
    }
    res2 = client.post("/api/documents/save", json=doc2_payload)
    assert res2.status_code == 201

    # List documents for this patient
    list_res = client.get(f"/api/patients/{patient_id}/documents")
    assert list_res.status_code == 200
    docs = list_res.json()["documents"]
    assert len(docs) == 2
    filenames = [d["filename"] for d in docs]
    assert "blood_test_oct2026.pdf" in filenames
    assert "discharge_summary.pdf" in filenames

    # Check updated document count in patient profile
    pat_res = client.get(f"/api/patients/{patient_id}")
    assert pat_res.json()["document_count"] == 2

    # Get single document detail
    detail_res = client.get(f"/api/documents/{doc1_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == doc1_id
    assert detail["filename"] == "blood_test_oct2026.pdf"
    assert len(detail["lab_results"]) == 1
    assert detail["lab_results"][0]["test_name"] == "HbA1c"


def test_update_document_metadata(client: TestClient) -> None:
    """Test PATCH /api/documents/{id} updates metadata."""
    p_res = client.post("/api/patients", json={"display_name": "Test Update Patient"})
    patient_id = p_res.json()["id"]

    save_res = client.post(
        "/api/documents/save",
        json={"patient_id": patient_id, "filename": "orig_file.pdf", "document_type": "Other"},
    )
    doc_id = save_res.json()["id"]

    # Update metadata
    patch_res = client.patch(
        f"/api/documents/{doc_id}",
        json={"filename": "renamed_report.pdf", "document_type": "Diagnostic Report", "summary": "Updated notes."},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["filename"] == "renamed_report.pdf"
    assert updated["document_type"] == "Diagnostic Report"
    assert updated["summary"] == "Updated notes."

    # Update non-existent document
    err_res = client.patch(f"/api/documents/{uuid.uuid4()}", json={"filename": "none.pdf"})
    assert err_res.status_code == 404


def test_cascade_delete_document_and_linked_records(client: TestClient, db_session: Session) -> None:
    """Deleting a document safely cascades and deletes all associated clinical entities."""
    p_res = client.post("/api/patients", json={"display_name": "Patient For Cascade Delete"})
    patient_id = p_res.json()["id"]

    # Save document with diagnoses, medications, and labs
    save_payload = {
        "patient_id": patient_id,
        "filename": "delete_target.pdf",
        "custom_diagnoses": [{"diagnosis": "Hypertension"}],
        "custom_medications": [{"name": "Amlodipine", "dose": "5 mg"}],
        "custom_lab_results": [{"test_name": "Serum Creatinine", "value": "1.0"}],
    }
    save_res = client.post("/api/documents/save", json=save_payload)
    doc_id = save_res.json()["id"]

    # Confirm records exist in DB
    assert db_session.query(MedicalDocument).filter(MedicalDocument.id == doc_id).count() == 1
    assert db_session.query(DiagnosisRecord).filter(DiagnosisRecord.document_id == doc_id).count() == 1
    assert db_session.query(MedicationRecord).filter(MedicationRecord.document_id == doc_id).count() == 1
    assert db_session.query(LabResultRecord).filter(LabResultRecord.document_id == doc_id).count() == 1

    # Delete document
    del_res = client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify all linked entities were deleted
    assert db_session.query(MedicalDocument).filter(MedicalDocument.id == doc_id).count() == 0
    assert db_session.query(DiagnosisRecord).filter(DiagnosisRecord.document_id == doc_id).count() == 0
    assert db_session.query(MedicationRecord).filter(MedicationRecord.document_id == doc_id).count() == 0
    assert db_session.query(LabResultRecord).filter(LabResultRecord.document_id == doc_id).count() == 0

    # Verify patient was NOT deleted
    assert db_session.query(Patient).filter(Patient.id == patient_id).count() == 1

    # Attempt to delete non-existent document
    del_again = client.delete(f"/api/documents/{doc_id}")
    assert del_again.status_code == 404
