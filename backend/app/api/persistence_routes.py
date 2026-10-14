"""FastAPI endpoints for PostgreSQL / SQLite persistence of patients and medical documents.

Provides endpoints for:
- Patient profiles (create, list, get)
- Medical documents (save with linked relational records in an atomic transaction, list, get detail, update metadata, cascade delete)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.models import (
    DiagnosisRecord,
    LabResultRecord,
    MedicalDocument,
    MedicationRecord,
    Patient,
)
from ..db.session import get_db
from ..schemas import (
    DiagnosisItem,
    DiagnosisRecordResponse,
    LabResultRecordResponse,
    LabTestItem,
    MedicalDocumentExtraction,
    MedicationItem,
    MedicationRecordResponse,
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    SaveDocumentRequest,
    SavedDocumentDetail,
    SavedDocumentListResponse,
    SavedDocumentSummary,
    TeluguExplainRequest,
    TeluguHealthSummary,
    UpdateDocumentRequest,
)
from ..services.fhir_exporter import (
    export_document_fhir_bundle,
    export_patient_fhir_bundle,
)
from ..services.gemini_extractor import (
    GeminiApiError,
    GeminiConfigError,
    GeminiInvalidOutputError,
    GeminiRateLimitError,
)
from ..services.telugu_explainer import explain_medical_extraction_in_telugu


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["persistence"])


def _to_doc_summary(doc: MedicalDocument) -> SavedDocumentSummary:
    """Helper to convert a MedicalDocument ORM object into SavedDocumentSummary."""
    return SavedDocumentSummary(
        id=doc.id,
        patient_id=doc.patient_id,
        filename=doc.filename,
        document_type=doc.document_type,
        upload_date=doc.upload_date,
        processing_status=doc.processing_status,
        ai_analysis_status=doc.ai_analysis_status,
        page_count=doc.page_count,
        total_char_count=doc.total_char_count,
        extraction_method=doc.extraction_method,
        confidence=doc.confidence,
        confidence_reason=doc.confidence_reason,
        summary=doc.summary,
        disclaimer=doc.disclaimer,
        model_used=doc.model_used,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        diagnoses_count=len(doc.diagnoses) if doc.diagnoses is not None else 0,
        medications_count=len(doc.medications) if doc.medications is not None else 0,
        lab_results_count=len(doc.lab_results) if doc.lab_results is not None else 0,
    )


def _to_doc_detail(doc: MedicalDocument) -> SavedDocumentDetail:
    """Helper to convert a MedicalDocument ORM object into SavedDocumentDetail."""
    summary = _to_doc_summary(doc)
    return SavedDocumentDetail(
        **summary.model_dump(),
        raw_text=doc.raw_text,
        ai_extraction_json=doc.ai_extraction_json,
        diagnoses=[DiagnosisRecordResponse.model_validate(d) for d in doc.diagnoses] if doc.diagnoses else [],
        medications=[MedicationRecordResponse.model_validate(m) for m in doc.medications] if doc.medications else [],
        lab_results=[LabResultRecordResponse.model_validate(l) for l in doc.lab_results] if doc.lab_results else [],
    )


# ============================================================================
# Patients Endpoints
# ============================================================================


@router.post(
    "/patients",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient profile",
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
) -> PatientResponse:
    """Create a new patient record."""
    try:
        patient = Patient(
            id=str(uuid.uuid4()),
            display_name=payload.display_name.strip(),
            age=payload.age.strip() if payload.age else None,
            gender=payload.gender.strip() if payload.gender else None,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return PatientResponse(
            id=patient.id,
            display_name=patient.display_name,
            age=patient.age,
            gender=patient.gender,
            document_count=0,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create patient: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create patient record: {str(exc)}",
        )


@router.get(
    "/patients",
    response_model=PatientListResponse,
    summary="List all patient profiles",
)
def list_patients(
    db: Session = Depends(get_db),
) -> PatientListResponse:
    """Retrieve all patient profiles with their document counts."""
    try:
        # Query patients and left join documents count
        query = (
            select(Patient, func.count(MedicalDocument.id).label("doc_count"))
            .outerjoin(MedicalDocument, Patient.id == MedicalDocument.patient_id)
            .group_by(Patient.id)
            .order_by(Patient.display_name)
        )
        results = db.execute(query).all()

        patients: list[PatientResponse] = []
        for patient, doc_count in results:
            patients.append(
                PatientResponse(
                    id=patient.id,
                    display_name=patient.display_name,
                    age=patient.age,
                    gender=patient.gender,
                    document_count=int(doc_count or 0),
                    created_at=patient.created_at,
                    updated_at=patient.updated_at,
                )
            )

        return PatientListResponse(patients=patients, total=len(patients))
    except Exception as exc:
        logger.exception("Failed to list patients: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query failure: {str(exc)}",
        )


@router.get(
    "/patients/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient profile by ID",
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
) -> PatientResponse:
    """Retrieve a single patient profile."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    doc_count = db.query(func.count(MedicalDocument.id)).filter(MedicalDocument.patient_id == patient.id).scalar() or 0
    return PatientResponse(
        id=patient.id,
        display_name=patient.display_name,
        age=patient.age,
        gender=patient.gender,
        document_count=int(doc_count),
        created_at=patient.created_at,
        updated_at=patient.updated_at,
    )


@router.get(
    "/patients/{patient_id}/documents",
    response_model=SavedDocumentListResponse,
    summary="List all saved documents for a patient",
)
def list_patient_documents(
    patient_id: str,
    db: Session = Depends(get_db),
) -> SavedDocumentListResponse:
    """Retrieve all saved documents and counts for a given patient."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )

    docs = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.patient_id == patient_id)
        .order_by(MedicalDocument.created_at.desc())
        .all()
    )

    summaries = [_to_doc_summary(doc) for doc in docs]
    return SavedDocumentListResponse(documents=summaries, total=len(summaries))


# ============================================================================
# Medical Documents Endpoints
# ============================================================================


@router.post(
    "/documents/save",
    response_model=SavedDocumentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Persist a medical document and its validated AI extraction transactionally",
)
def save_document(
    payload: SaveDocumentRequest,
    db: Session = Depends(get_db),
) -> SavedDocumentDetail:
    """Persist a medical document and its normalized clinical findings atomically.

    Guarantees:
    - Entire operation executes within a single database transaction.
    - If any error occurs, all changes are rolled back.
    - Never silently overwrites existing records.
    - Normalizes diagnoses, medications, and lab results into relational tables.
    """
    # 1. Validate patient existence
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID '{payload.patient_id}' does not exist.",
        )

    # 2. Prepare document record
    doc_id = str(uuid.uuid4())
    upload_date = payload.upload_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # AI snapshot
    ai_snapshot: dict[str, Any] | None = None
    if payload.ai_extraction is not None:
        ai_snapshot = payload.ai_extraction.model_dump()

    confidence = payload.confidence or (payload.ai_extraction.confidence if payload.ai_extraction else None)
    confidence_reason = payload.confidence_reason or (
        payload.ai_extraction.confidence_reason if payload.ai_extraction else None
    )
    summary = payload.summary or (payload.ai_extraction.summary if payload.ai_extraction else None)

    try:
        doc = MedicalDocument(
            id=doc_id,
            patient_id=patient.id,
            filename=payload.filename,
            document_type=payload.document_type,
            upload_date=upload_date,
            processing_status=payload.processing_status,
            ai_analysis_status=payload.ai_analysis_status,
            page_count=payload.page_count,
            total_char_count=payload.total_char_count,
            extraction_method=payload.extraction_method,
            confidence=confidence,
            confidence_reason=confidence_reason,
            summary=summary,
            disclaimer=payload.disclaimer,
            model_used=payload.model_used,
            raw_text=payload.raw_text,
            ai_extraction_json=ai_snapshot,
        )
        db.add(doc)

        # 3. Add diagnoses
        raw_diagnoses = (
            payload.custom_diagnoses
            if payload.custom_diagnoses is not None
            else (payload.ai_extraction.diagnoses if payload.ai_extraction else [])
        )
        for diag in raw_diagnoses:
            diag_text = getattr(diag, "diagnosis", None) or getattr(diag, "condition", "Unknown")
            diag_rec = DiagnosisRecord(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                patient_id=patient.id,
                diagnosis=diag_text,
                status=diag.status,
                evidence=diag.evidence,
                page_number=diag.page_number,
            )
            db.add(diag_rec)

        raw_medications = (
            payload.custom_medications
            if payload.custom_medications is not None
            else (
                (getattr(payload.ai_extraction, "medicines", None) or getattr(payload.ai_extraction, "medications", []))
                if payload.ai_extraction
                else []
            )
        )
        for med in raw_medications:
            med_rec = MedicationRecord(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                patient_id=patient.id,
                name=med.name,
                dose=med.dose,
                frequency=med.frequency,
                duration=med.duration,
                route=med.route,
                instructions=med.instructions,
                evidence=med.evidence,
                page_number=med.page_number,
            )
            db.add(med_rec)

        # 5. Add lab results
        raw_labs = (
            payload.custom_lab_results
            if payload.custom_lab_results is not None
            else (payload.ai_extraction.lab_tests if payload.ai_extraction else [])
        )
        for lab in raw_labs:
            is_abnormal = (
                getattr(lab, "abnormal_flag", None)
                if getattr(lab, "abnormal_flag", None) is not None
                else getattr(lab, "is_abnormal", None)
            )
            lab_rec = LabResultRecord(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                patient_id=patient.id,
                test_name=lab.test_name,
                value=lab.value,
                unit=lab.unit,
                reference_range=lab.reference_range,
                abnormal_flag=is_abnormal,
                evidence=lab.evidence,
                page_number=lab.page_number,
            )
            db.add(lab_rec)

        # 6. Commit transaction atomically
        db.commit()
        db.refresh(doc)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to persist document transactionally: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failed: {str(exc)}",
        )

    return _to_doc_detail(doc)


@router.get(
    "/documents",
    response_model=SavedDocumentListResponse,
    summary="List all saved documents (optionally filtered by patient)",
)
def list_all_documents(
    patient_id: str | None = Query(None, description="Optional patient UUID filter"),
    db: Session = Depends(get_db),
) -> SavedDocumentListResponse:
    """List persisted documents ordered by creation date."""
    query = db.query(MedicalDocument)
    if patient_id:
        query = query.filter(MedicalDocument.patient_id == patient_id)
    docs = query.order_by(MedicalDocument.created_at.desc()).all()
    summaries = [_to_doc_summary(doc) for doc in docs]
    return SavedDocumentListResponse(documents=summaries, total=len(summaries))


@router.get(
    "/documents/{document_id}",
    response_model=SavedDocumentDetail,
    summary="Retrieve one document with full extracted information and clinical entities",
)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
) -> SavedDocumentDetail:
    """Retrieve full detail of a saved document."""
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' not found.",
        )
    return _to_doc_detail(doc)


@router.patch(
    "/documents/{document_id}",
    response_model=SavedDocumentDetail,
    summary="Update document metadata",
)
def update_document(
    document_id: str,
    payload: UpdateDocumentRequest,
    db: Session = Depends(get_db),
) -> SavedDocumentDetail:
    """Update metadata for an existing medical document."""
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' not found.",
        )

    try:
        if payload.filename is not None:
            doc.filename = payload.filename.strip()
        if payload.document_type is not None:
            doc.document_type = payload.document_type.strip()
        if payload.summary is not None:
            doc.summary = payload.summary.strip()

        doc.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(doc)
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update document %s: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document: {str(exc)}",
        )

    return _to_doc_detail(doc)


@router.delete(
    "/documents/{document_id}",
    summary="Delete a document and its linked records safely",
)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a medical document and all linked diagnoses, medications, and lab results."""
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' not found.",
        )

    try:
        db.delete(doc)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to delete document %s: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(exc)}",
        )

    return {
        "status": "deleted",
        "id": document_id,
        "message": f"Document '{doc.filename}' and its linked records were safely deleted.",
    }


# ============================================================================
# FHIR R4 Interoperability Endpoints (Step 7)
# ============================================================================


@router.get(
    "/patients/{patient_id}/fhir",
    summary="Export patient records as an HL7 FHIR R4 collection Bundle JSON",
)
def get_patient_fhir(
    patient_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Export all persisted medical records for a patient as a valid FHIR R4 collection Bundle."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return export_patient_fhir_bundle(patient)


@router.get(
    "/documents/{document_id}/fhir",
    summary="Export a single document and its clinical entities as an HL7 FHIR R4 Bundle JSON",
)
def get_document_fhir(
    document_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Export a single document and its linked diagnoses, medications, and labs as a FHIR R4 Bundle."""
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' not found.",
        )
    return export_document_fhir_bundle(doc)


# ============================================================================
# Telugu Health Summary Endpoints (Step 7)
# ============================================================================


@router.post(
    "/documents/explain-telugu",
    response_model=TeluguHealthSummary,
    summary="Generate a patient-friendly Telugu explanation of clinical findings",
)
def explain_extraction_telugu(
    payload: TeluguExplainRequest,
) -> TeluguHealthSummary:
    """Generate patient-friendly Telugu explanations for clinical diagnoses, medicines, and labs.

    Preserves exact dosages, units, and medicine names while generating natural Telugu explanations.
    """
    if not payload.extraction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A validated extraction object is required to generate a Telugu explanation.",
        )

    try:
        return explain_medical_extraction_in_telugu(payload.extraction)
    except GeminiConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        )
    except GeminiRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message
        )
    except GeminiInvalidOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message
        )
    except GeminiApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message
        )
    except Exception as exc:
        logger.exception("Unexpected failure during Telugu explanation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Telugu explanation: {str(exc)}",
        )


@router.get(
    "/documents/{document_id}/explain-telugu",
    response_model=TeluguHealthSummary,
    summary="Generate Telugu explanation for a saved medical document",
)
def explain_saved_document_telugu(
    document_id: str,
    db: Session = Depends(get_db),
) -> TeluguHealthSummary:
    """Fetch a saved document from PostgreSQL and generate its patient-friendly Telugu explanation."""
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' not found.",
        )

    # Reconstruct extraction from JSON snapshot or relational records
    if doc.ai_extraction_json:
        try:
            extraction = MedicalDocumentExtraction.model_validate(doc.ai_extraction_json)
        except Exception:
            extraction = None
    else:
        extraction = None

    if extraction is None:
        extraction = MedicalDocumentExtraction(
            document_type=doc.document_type,
            report_date=doc.upload_date,
            patient_name=doc.patient.display_name if doc.patient else None,
            diagnoses=[
                DiagnosisItem(
                    diagnosis=d.diagnosis,
                    status=d.status,
                    evidence=d.evidence,
                    page_number=d.page_number,
                )
                for d in doc.diagnoses
            ],
            medicines=[
                MedicationItem(
                    name=m.name,
                    dose=m.dose,
                    frequency=m.frequency,
                    duration=m.duration,
                    route=m.route,
                    instructions=m.instructions,
                    evidence=m.evidence,
                    page_number=m.page_number,
                )
                for m in doc.medications
            ],
            lab_tests=[
                LabTestItem(
                    test_name=l.test_name,
                    value=l.value,
                    unit=l.unit,
                    reference_range=l.reference_range,
                    abnormal_flag=l.abnormal_flag,
                    evidence=l.evidence,
                    page_number=l.page_number,
                )
                for l in doc.lab_results
            ],
            summary=doc.summary,
            disclaimer=doc.disclaimer,
            confidence=doc.confidence if doc.confidence in ("high", "medium", "low") else "high",  # type: ignore
            model_used=doc.model_used or "gemini-3.1-flash-lite",
        )

    try:
        return explain_medical_extraction_in_telugu(extraction)
    except GeminiConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=exc.message
        )
    except GeminiRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message
        )
    except GeminiInvalidOutputError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message
        )
    except GeminiApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message
        )
    except Exception as exc:
        logger.exception("Unexpected failure during Telugu explanation for doc %s: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Telugu explanation: {str(exc)}",
        )

