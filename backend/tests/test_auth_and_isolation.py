"""Comprehensive Automated Tests for Backend Authorization and Patient Isolation (Phase 2).

Validates:
1. Unauthenticated rejection (401 Unauthorized) across all private endpoints:
   - PDF extraction, OCR extraction, AI clinical analysis
   - Patient creation, listing, retrieval, patient documents listing
   - Document persistence (save), listing, retrieval, update, deletion
   - FHIR R4 exports (patient and document)
   - Telugu explanations (extraction and saved document)
   - Chat conversations (list, create, get, delete, send message, quick chat)
2. Public endpoints remain appropriately accessible:
   - Health check (/health)
   - User registration (POST /api/auth/register)
   - User login (POST /api/auth/login)
3. Patient isolation:
   - User A can access only patients linked to User A's user_id.
   - User B cannot see, retrieve, or list User A's patients.
4. Document isolation:
   - Documents are strictly scoped to the authenticated user's patient.
   - User B cannot view, patch, delete, export, or explain User A's documents.
   - User B cannot save a document against User A's patient ID.
5. Chat conversation isolation:
   - User B cannot access, list, message, or delete User A's conversations.
   - User B cannot tamper with conversation IDs across different patients.
6. Demo record association:
   - Default fictional demo patient (Smt. Sunita Rao) is safely bound to demo user.
   - Unauthorized users cannot access demo patient records.
"""

from __future__ import annotations

import io
import uuid
from typing import Generator

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.init_db import (
    DEFAULT_DEMO_PATIENT_ID,
    DEFAULT_DEMO_USER_EMAIL,
    DEFAULT_DEMO_USER_ID,
    DEFAULT_DEMO_USER_PASSWORD,
    init_database,
)
from app.db.models import (
    ChatConversation,
    MedicalDocument,
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


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None, None, None]:
    """Create fresh isolated tables before each test and drop them after."""
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
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Yield a FastAPI TestClient wired to the in-memory test database."""
    def _override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _make_dummy_pdf() -> bytes:
    """Create a minimal 1-page PDF for upload tests."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 700), "Confidential Patient Clinical Report")
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ============================================================================
# 1. Unauthenticated Access Tests (All Private Endpoints Return 401)
# ============================================================================


def test_unauthenticated_document_processing_endpoints(client: TestClient) -> None:
    """Verify document processing endpoints require valid authentication."""
    pdf_bytes = _make_dummy_pdf()
    files = {"file": ("report.pdf", pdf_bytes, "application/pdf")}

    # PDF selectable text extraction
    res_pdf = client.post("/api/documents/extract-text", files=files)
    assert res_pdf.status_code == 401
    assert "token is required" in res_pdf.json()["detail"].lower()

    # OCR text extraction
    res_ocr = client.post("/api/documents/extract-text-ocr", files=files)
    assert res_ocr.status_code == 401
    assert "token is required" in res_ocr.json()["detail"].lower()

    # AI clinical analysis
    res_ai = client.post("/api/documents/analyze-ai", json={"text": "Hemoglobin 14.2 g/dL"})
    assert res_ai.status_code == 401
    assert "token is required" in res_ai.json()["detail"].lower()


def test_unauthenticated_patient_and_document_persistence_endpoints(client: TestClient) -> None:
    """Verify persistence endpoints reject requests missing an authentication token."""
    dummy_uuid = str(uuid.uuid4())

    # Patients endpoints
    assert client.post("/api/patients", json={"display_name": "Test"}).status_code == 401
    assert client.get("/api/patients").status_code == 401
    assert client.get(f"/api/patients/{dummy_uuid}").status_code == 401
    assert client.get(f"/api/patients/{dummy_uuid}/documents").status_code == 401

    # Medical documents endpoints
    assert client.post("/api/documents/save", json={"patient_id": dummy_uuid, "filename": "test.pdf"}).status_code == 401
    assert client.get("/api/documents").status_code == 401
    assert client.get(f"/api/documents/{dummy_uuid}").status_code == 401
    assert client.patch(f"/api/documents/{dummy_uuid}", json={"filename": "updated.pdf"}).status_code == 401
    assert client.delete(f"/api/documents/{dummy_uuid}").status_code == 401

    # FHIR export endpoints
    assert client.get(f"/api/patients/{dummy_uuid}/fhir").status_code == 401
    assert client.get(f"/api/documents/{dummy_uuid}/fhir").status_code == 401

    # Telugu summary endpoints
    assert client.post("/api/documents/explain-telugu", json={"extraction": {}}).status_code == 401
    assert client.get(f"/api/documents/{dummy_uuid}/explain-telugu").status_code == 401


def test_unauthenticated_chat_endpoints(client: TestClient) -> None:
    """Verify all health AI chat endpoints reject unauthenticated access."""
    dummy_patient_id = str(uuid.uuid4())
    dummy_conv_id = str(uuid.uuid4())

    assert client.get(f"/api/patients/{dummy_patient_id}/conversations").status_code == 401
    assert client.post(f"/api/patients/{dummy_patient_id}/conversations", json={}).status_code == 401
    assert client.get(f"/api/patients/{dummy_patient_id}/conversations/{dummy_conv_id}").status_code == 401
    assert client.delete(f"/api/patients/{dummy_patient_id}/conversations/{dummy_conv_id}").status_code == 401
    assert client.post(f"/api/patients/{dummy_patient_id}/conversations/{dummy_conv_id}/messages", json={"message": "Hi"}).status_code == 401
    assert client.post(f"/api/patients/{dummy_patient_id}/chat", json={"message": "Hi"}).status_code == 401


def test_invalid_and_forged_tokens_rejected(client: TestClient) -> None:
    """Verify invalid or forged JWT tokens receive 401 Unauthorized."""
    # Malformed garbage
    headers_malformed = {"Authorization": "Bearer not-a-valid-jwt-token"}
    res1 = client.get("/api/patients", headers=headers_malformed)
    assert res1.status_code == 401

    # Forged signature token
    headers_forged = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmYWtlLXVzZXIifQ.invalidsignature123"}
    res2 = client.get("/api/patients", headers=headers_forged)
    assert res2.status_code == 401


# ============================================================================
# 2. Public Endpoints Accessibility
# ============================================================================


def test_public_endpoints_accessible(client: TestClient) -> None:
    """Verify public endpoints do not require authentication."""
    # Health check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # Registration endpoint
    res_reg = client.post(
        "/api/auth/register",
        json={
            "email": "dr.rao@example.com",
            "password": "SecurePassword@123",
            "full_name": "Dr. Rao",
        },
    )
    assert res_reg.status_code == 201

    # Login endpoint
    res_login = client.post(
        "/api/auth/login",
        json={
            "email": "dr.rao@example.com",
            "password": "SecurePassword@123",
        },
    )
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()


# ============================================================================
# 3. Patient Isolation Tests (Multi-tenant Ownership Scoping)
# ============================================================================


def _create_user_and_headers(client: TestClient, email: str, name: str) -> dict[str, str]:
    """Helper to register and login a test user, returning auth headers."""
    client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!", "full_name": name},
    )
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_patient_list_and_get_isolation(client: TestClient) -> None:
    """Verify User B cannot see or retrieve User A's patient records."""
    headers_a = _create_user_and_headers(client, "alice@hospital.local", "Dr. Alice")
    headers_b = _create_user_and_headers(client, "bob@clinic.local", "Dr. Bob")

    # User A creates Patient A
    p_a_res = client.post(
        "/api/patients",
        headers=headers_a,
        json={"display_name": "Patient Alpha (Alice)", "age": "45", "gender": "Female"},
    )
    assert p_a_res.status_code == 201
    patient_a_id = p_a_res.json()["id"]

    # User B creates Patient B
    p_b_res = client.post(
        "/api/patients",
        headers=headers_b,
        json={"display_name": "Patient Beta (Bob)", "age": "50", "gender": "Male"},
    )
    assert p_b_res.status_code == 201
    patient_b_id = p_b_res.json()["id"]

    # User A lists patients -> sees only own profiles (including auto-created primary), Bob's profiles are completely absent
    list_a = client.get("/api/patients", headers=headers_a).json()["patients"]
    list_a_ids = [p["id"] for p in list_a]
    assert patient_a_id in list_a_ids
    assert patient_b_id not in list_a_ids
    assert all(p["display_name"] not in ("Dr. Bob", "Patient Beta (Bob)") for p in list_a)

    # User B lists patients -> sees only own profiles, Alice's profiles are completely absent
    list_b = client.get("/api/patients", headers=headers_b).json()["patients"]
    list_b_ids = [p["id"] for p in list_b]
    assert patient_b_id in list_b_ids
    assert patient_a_id not in list_b_ids
    assert all(p["display_name"] not in ("Dr. Alice", "Patient Alpha (Alice)") for p in list_b)

    # User B tries to directly read Patient Alpha -> 403 Forbidden
    res_b_get_a = client.get(f"/api/patients/{patient_a_id}", headers=headers_b)
    assert res_b_get_a.status_code == 403
    assert "access denied" in res_b_get_a.json()["detail"].lower()

    # User B tries to read Patient Alpha documents -> 403 Forbidden
    res_b_docs_a = client.get(f"/api/patients/{patient_a_id}/documents", headers=headers_b)
    assert res_b_docs_a.status_code == 403

    # User B tries to export FHIR for Patient Alpha -> 403 Forbidden
    res_b_fhir_a = client.get(f"/api/patients/{patient_a_id}/fhir", headers=headers_b)
    assert res_b_fhir_a.status_code == 403


# ============================================================================
# 4. Document Isolation Tests (Save, View, Patch, Delete)
# ============================================================================


def test_document_cross_user_isolation(client: TestClient) -> None:
    """Verify medical documents cannot be accessed, modified, or deleted by another user."""
    headers_a = _create_user_and_headers(client, "doc_user_a@test.local", "User A")
    headers_b = _create_user_and_headers(client, "doc_user_b@test.local", "User B")

    # Create Patient A and Patient B
    p_a = client.post("/api/patients", headers=headers_a, json={"display_name": "Kamala A"}).json()
    p_b = client.post("/api/patients", headers=headers_b, json={"display_name": "Suresh B"}).json()

    # 1. User B tries to save a document under Patient A -> 403 Forbidden
    res_b_save_a = client.post(
        "/api/documents/save",
        headers=headers_b,
        json={
            "patient_id": p_a["id"],
            "filename": "malicious_injection.pdf",
            "document_type": "Lab Report",
        },
    )
    assert res_b_save_a.status_code == 403
    assert "access denied" in res_b_save_a.json()["detail"].lower()

    # 2. User A successfully saves a document
    res_a_save = client.post(
        "/api/documents/save",
        headers=headers_a,
        json={
            "patient_id": p_a["id"],
            "filename": "kamala_prescription.pdf",
            "document_type": "Prescription",
            "summary": "Type 2 Diabetes consultation",
        },
    )
    assert res_a_save.status_code == 201
    doc_a_id = res_a_save.json()["id"]

    # 3. User B lists all documents -> doc_a is NOT present
    docs_b = client.get("/api/documents", headers=headers_b).json()["documents"]
    assert all(d["id"] != doc_a_id for d in docs_b)

    # 4. User B tries to list documents filtering by Patient A -> 403 Forbidden
    res_b_filter = client.get(f"/api/documents?patient_id={p_a['id']}", headers=headers_b)
    assert res_b_filter.status_code == 403

    # 5. User B tries to read Document A detail -> 403 Forbidden
    res_b_get_doc = client.get(f"/api/documents/{doc_a_id}", headers=headers_b)
    assert res_b_get_doc.status_code == 403

    # 6. User B tries to update Document A metadata -> 403 Forbidden
    res_b_patch = client.patch(
        f"/api/documents/{doc_a_id}",
        headers=headers_b,
        json={"filename": "tampered.pdf"},
    )
    assert res_b_patch.status_code == 403

    # 7. User B tries to export FHIR for Document A -> 403 Forbidden
    res_b_fhir = client.get(f"/api/documents/{doc_a_id}/fhir", headers=headers_b)
    assert res_b_fhir.status_code == 403

    # 8. User B tries to delete Document A -> 403 Forbidden
    res_b_del = client.delete(f"/api/documents/{doc_a_id}", headers=headers_b)
    assert res_b_del.status_code == 403

    # 9. User A can successfully retrieve, update, and delete Document A
    res_a_get = client.get(f"/api/documents/{doc_a_id}", headers=headers_a)
    assert res_a_get.status_code == 200
    assert res_a_get.json()["filename"] == "kamala_prescription.pdf"

    res_a_patch = client.patch(
        f"/api/documents/{doc_a_id}",
        headers=headers_a,
        json={"summary": "Updated diabetes consultation"},
    )
    assert res_a_patch.status_code == 200

    res_a_del = client.delete(f"/api/documents/{doc_a_id}", headers=headers_a)
    assert res_a_del.status_code == 200
    assert res_a_del.json()["status"] == "deleted"


# ============================================================================
# 5. Chat Conversation Isolation Tests
# ============================================================================


def test_chat_cross_user_isolation(client: TestClient) -> None:
    """Verify chat conversations and messages are strictly patient- and user-isolated."""
    headers_a = _create_user_and_headers(client, "chat_user_a@test.local", "User A")
    headers_b = _create_user_and_headers(client, "chat_user_b@test.local", "User B")

    # Patient A and Patient B
    p_a = client.post("/api/patients", headers=headers_a, json={"display_name": "Patient Alpha"}).json()
    p_b = client.post("/api/patients", headers=headers_b, json={"display_name": "Patient Beta"}).json()

    # User A creates Conversation A
    conv_a = client.post(
        f"/api/patients/{p_a['id']}/conversations",
        headers=headers_a,
        json={"title": "Private Consultation Alpha"},
    ).json()
    conv_a_id = conv_a["id"]

    # 1. User B attempts to list conversations for Patient A -> 403 Forbidden
    assert client.get(f"/api/patients/{p_a['id']}/conversations", headers=headers_b).status_code == 403

    # 2. User B attempts to create conversation for Patient A -> 403 Forbidden
    assert client.post(f"/api/patients/{p_a['id']}/conversations", headers=headers_b, json={"title": "Hacked"}).status_code == 403

    # 3. User B attempts to get Conversation A using Patient A's path -> 403 Forbidden
    assert client.get(f"/api/patients/{p_a['id']}/conversations/{conv_a_id}", headers=headers_b).status_code == 403

    # 4. User B attempts to delete Conversation A using Patient A's path -> 403 Forbidden
    assert client.delete(f"/api/patients/{p_a['id']}/conversations/{conv_a_id}", headers=headers_b).status_code == 403

    # 5. User B attempts to post message to Conversation A using Patient A's path -> 403 Forbidden
    assert client.post(
        f"/api/patients/{p_a['id']}/conversations/{conv_a_id}/messages",
        headers=headers_b,
        json={"message": "Unauthorized inquiry"},
    ).status_code == 403

    # 6. User B attempts quick chat on Patient A -> 403 Forbidden
    assert client.post(
        f"/api/patients/{p_a['id']}/chat",
        headers=headers_b,
        json={"message": "Inquiry"},
    ).status_code == 403

    # 7. User B attempts to access Conversation A via User B's own Patient B path -> 404 Not Found (mismatched patient)
    res_spoof = client.get(f"/api/patients/{p_b['id']}/conversations/{conv_a_id}", headers=headers_b)
    assert res_spoof.status_code == 404
    assert "not found for patient" in res_spoof.json()["detail"].lower()

    # 8. User A can access and delete their own conversation
    assert client.get(f"/api/patients/{p_a['id']}/conversations/{conv_a_id}", headers=headers_a).status_code == 200
    assert client.delete(f"/api/patients/{p_a['id']}/conversations/{conv_a_id}", headers=headers_a).status_code == 200


# ============================================================================
# 6. Demo Record Association Safety Tests
# ============================================================================


def test_demo_user_and_patient_safety(client: TestClient, db_session: Session) -> None:
    """Verify demo patient 'Smt. Sunita Rao' is associated with demo user and isolated from others."""
    # Run init_database seeding on test_engine
    init_database(test_engine)

    # Verify demo user exists in database
    demo_user = db_session.scalar(select(User).where(User.email == DEFAULT_DEMO_USER_EMAIL))
    assert demo_user is not None
    assert demo_user.id == DEFAULT_DEMO_USER_ID

    # Verify demo patient exists and has demo user_id
    demo_patient = db_session.scalar(select(Patient).where(Patient.id == DEFAULT_DEMO_PATIENT_ID))
    assert demo_patient is not None
    assert demo_patient.user_id == DEFAULT_DEMO_USER_ID

    # Log in as demo user
    login_res = client.post(
        "/api/auth/login",
        json={"email": DEFAULT_DEMO_USER_EMAIL, "password": DEFAULT_DEMO_USER_PASSWORD},
    )
    assert login_res.status_code == 200
    demo_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Demo user can access demo patient
    res_demo = client.get(f"/api/patients/{DEFAULT_DEMO_PATIENT_ID}", headers=demo_headers)
    assert res_demo.status_code == 200
    assert res_demo.json()["display_name"] == "Smt. Sunita Rao"

    # Another user cannot access demo patient
    headers_intruder = _create_user_and_headers(client, "intruder@evil.local", "Intruder")
    res_intruder = client.get(f"/api/patients/{DEFAULT_DEMO_PATIENT_ID}", headers=headers_intruder)
    assert res_intruder.status_code == 403
    assert "access denied" in res_intruder.json()["detail"].lower()
