"""Tests for FHIR R4 Interoperability and Bundle Export Service (Step 7).

Validates:
- Patient and document conversion to HL7 FHIR R4 standard resources:
  - Patient
  - DocumentReference
  - Condition
  - MedicationStatement
  - Observation
  - Bundle (type: collection)
- Consistent cross-resource referencing (Patient/{id}, DocumentReference/{id}).
- Proper parsing of numerical lab values into valueQuantity.
- Proper mapping of abnormal flags to FHIR Observation interpretation codes.
- Error handling for missing records (404).
"""

from __future__ import annotations

import base64
import uuid
from typing import Generator

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

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

_TEST_USER_ID = "test-user-fhir-id"


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        id=_TEST_USER_ID,
        email="fhir@test.local",
        hashed_password="pw",
        full_name="FHIR Tester",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client(test_user: User) -> Generator[TestClient, None, None]:
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


def test_export_patient_fhir_bundle(client: TestClient) -> None:
    """Test exporting a patient's complete health history as an HL7 FHIR R4 Bundle."""
    # 1. Create Patient
    p_res = client.post(
        "/api/patients",
        json={"display_name": "Sri Ramesh Varma", "age": "48", "gender": "Male"},
    )
    assert p_res.status_code == 201
    patient_id = p_res.json()["id"]

    # 2. Save Document with Diagnoses, Medications, and Lab Results
    save_payload = {
        "patient_id": patient_id,
        "filename": "hyderabad_clinic_visit.pdf",
        "document_type": "Prescription",
        "upload_date": "2026-10-12",
        "raw_text": "APOLLO CLINIC - HYDERABAD\nRx: Tab Metformin 500 mg",
        "custom_diagnoses": [
            {
                "diagnosis": "Type 2 Diabetes Mellitus",
                "status": "active",
                "evidence": "CLINICAL IMPRESSION: Type 2 Diabetes Mellitus",
                "page_number": 1,
            }
        ],
        "custom_medications": [
            {
                "name": "Tab. Metformin HCl",
                "dose": "500 mg",
                "frequency": "1-0-1",
                "duration": "30 days",
                "route": "oral",
                "instructions": "after food",
                "evidence": "Tab. Metformin HCl 500 mg 1-0-1 after food",
                "page_number": 1,
            }
        ],
        "custom_lab_results": [
            {
                "test_name": "Fasting Blood Sugar",
                "value": "142",
                "unit": "mg/dL",
                "reference_range": "70 - 100 mg/dL",
                "abnormal_flag": True,
                "evidence": "Fasting Blood Sugar: 142 mg/dL (HIGH)",
                "page_number": 1,
            }
        ],
    }
    doc_res = client.post("/api/documents/save", json=save_payload)
    assert doc_res.status_code == 201
    doc_id = doc_res.json()["id"]

    # 3. Request FHIR Export
    fhir_res = client.get(f"/api/patients/{patient_id}/fhir")
    assert fhir_res.status_code == 200, fhir_res.text
    bundle = fhir_res.json()

    # Validate Bundle wrapper
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["id"] == f"patient-{patient_id}-fhir-bundle"
    assert bundle["total"] == 5  # Patient + DocumentReference + Condition + MedicationStatement + Observation
    assert len(bundle["entry"]) == 5

    # Group resources by resourceType
    resources_by_type = {}
    for entry in bundle["entry"]:
        res = entry["resource"]
        resources_by_type[res["resourceType"]] = res

    # Validate Patient resource
    pat = resources_by_type["Patient"]
    assert pat["id"] == patient_id
    assert pat["name"][0]["text"] == "Sri Ramesh Varma"
    assert pat["gender"] == "male"
    assert pat["extension"][0]["valueString"] == "48 years"

    # Validate DocumentReference resource
    doc_ref = resources_by_type["DocumentReference"]
    assert doc_ref["id"] == doc_id
    assert doc_ref["subject"]["reference"] == f"Patient/{patient_id}"
    assert doc_ref["type"]["text"] == "Prescription"
    assert doc_ref["content"][0]["attachment"]["title"] == "hyderabad_clinic_visit.pdf"
    # Verify base64 decoded raw text
    b64_data = doc_ref["content"][0]["attachment"]["data"]
    decoded = base64.b64decode(b64_data).decode("utf-8")
    assert "APOLLO CLINIC" in decoded

    # Validate Condition resource
    cond = resources_by_type["Condition"]
    assert cond["subject"]["reference"] == f"Patient/{patient_id}"
    assert cond["code"]["text"] == "Type 2 Diabetes Mellitus"
    assert cond["evidence"][0]["detail"][0]["reference"] == f"DocumentReference/{doc_id}"
    assert cond["clinicalStatus"]["coding"][0]["code"] == "active"

    # Validate MedicationStatement resource
    med_res = resources_by_type["MedicationStatement"]
    assert med_res["subject"]["reference"] == f"Patient/{patient_id}"
    assert med_res["medicationCodeableConcept"]["text"] == "Tab. Metformin HCl"
    assert med_res["derivedFrom"][0]["reference"] == f"DocumentReference/{doc_id}"
    assert "500 mg" in med_res["dosage"][0]["text"]
    assert med_res["dosage"][0]["patientInstruction"] == "after food"

    # Validate Observation resource
    obs = resources_by_type["Observation"]
    assert obs["subject"]["reference"] == f"Patient/{patient_id}"
    assert obs["derivedFrom"][0]["reference"] == f"DocumentReference/{doc_id}"
    assert obs["code"]["text"] == "Fasting Blood Sugar"
    assert obs["valueQuantity"]["value"] == 142.0
    assert obs["valueQuantity"]["unit"] == "mg/dL"
    assert obs["referenceRange"][0]["text"] == "70 - 100 mg/dL"
    assert obs["interpretation"][0]["coding"][0]["code"] == "A"


def test_export_document_fhir_bundle(client: TestClient) -> None:
    """Test exporting a single document and its clinical entities as a FHIR Bundle."""
    p_res = client.post("/api/patients", json={"display_name": "Smt. Sunita Rao"})
    patient_id = p_res.json()["id"]

    save_payload = {
        "patient_id": patient_id,
        "filename": "lab_report.pdf",
        "custom_lab_results": [
            {
                "test_name": "Serum Creatinine",
                "value": "0.9",
                "unit": "mg/dL",
                "reference_range": "0.6 - 1.2 mg/dL",
                "abnormal_flag": False,
            }
        ],
    }
    doc_res = client.post("/api/documents/save", json=save_payload)
    doc_id = doc_res.json()["id"]

    res = client.get(f"/api/documents/{doc_id}/fhir")
    assert res.status_code == 200
    bundle = res.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["id"] == f"doc-{doc_id}-fhir-bundle"
    types_in_bundle = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "Patient" in types_in_bundle
    assert "DocumentReference" in types_in_bundle
    assert "Observation" in types_in_bundle


def test_export_empty_patient_fhir_bundle(client: TestClient) -> None:
    """A patient with 0 records exports a valid Bundle containing just the Patient resource."""
    p_res = client.post("/api/patients", json={"display_name": "New Patient No Records"})
    patient_id = p_res.json()["id"]

    res = client.get(f"/api/patients/{patient_id}/fhir")
    assert res.status_code == 200
    bundle = res.json()
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Patient"


def test_export_fhir_not_found(client: TestClient) -> None:
    """Non-existent patient or document returns HTTP 404."""
    res_pat = client.get(f"/api/patients/{uuid.uuid4()}/fhir")
    assert res_pat.status_code == 404

    res_doc = client.get(f"/api/documents/{uuid.uuid4()}/fhir")
    assert res_doc.status_code == 404
