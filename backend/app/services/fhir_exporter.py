"""FHIR R4-inspired export service for Personal Health Copilot.

Transforms persisted patient, document, diagnosis, medication, and lab result entities
into standardized HL7 FHIR R4 JSON resources and Bundle collections.

Resources generated:
- Patient (http://hl7.org/fhir/StructureDefinition/Patient)
- DocumentReference (http://hl7.org/fhir/StructureDefinition/DocumentReference)
- Condition (http://hl7.org/fhir/StructureDefinition/Condition)
- MedicationStatement (http://hl7.org/fhir/StructureDefinition/MedicationStatement)
- Observation (http://hl7.org/fhir/StructureDefinition/Observation)
- Bundle (http://hl7.org/fhir/StructureDefinition/Bundle)
"""

from __future__ import annotations

import base64
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from ..db.models import (
    DiagnosisRecord,
    LabResultRecord,
    MedicalDocument,
    MedicationRecord,
    Patient,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_numeric(val_str: str | None) -> float | None:
    """Attempt to parse a float from a string (e.g. '142', '7.4', '<0.1')."""
    if not val_str:
        return None
    cleaned = val_str.strip().replace(",", "")
    match = re.search(r"[-+]?\d*\.?\d+", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def patient_to_fhir(patient: Patient) -> dict[str, Any]:
    """Convert Patient ORM model to a FHIR R4 Patient resource."""
    gender_map = {
        "female": "female",
        "f": "female",
        "male": "male",
        "m": "male",
        "other": "other",
    }
    raw_gender = (patient.gender or "").strip().lower()
    fhir_gender = gender_map.get(raw_gender, "unknown")

    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient.id,
        "identifier": [
            {
                "use": "official",
                "system": "urn:ietf:rfc:3986",
                "value": f"urn:uuid:{patient.id}",
            }
        ],
        "active": True,
        "name": [
            {
                "use": "usual",
                "text": patient.display_name,
            }
        ],
        "gender": fhir_gender,
    }

    if patient.age:
        resource["extension"] = [
            {
                "url": "http://hl7.org/fhir/StructureDefinition/patient-age",
                "valueString": f"{patient.age} years",
            }
        ]

    return resource


def document_to_fhir(doc: MedicalDocument) -> dict[str, Any]:
    """Convert MedicalDocument ORM model to a FHIR R4 DocumentReference resource."""
    content_item: dict[str, Any] = {
        "attachment": {
            "contentType": "text/plain",
            "title": doc.filename,
        }
    }
    if doc.raw_text:
        content_item["attachment"]["data"] = base64.b64encode(
            doc.raw_text.encode("utf-8")
        ).decode("ascii")

    resource: dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": doc.id,
        "status": "current",
        "docStatus": "final",
        "type": {
            "text": doc.document_type or "Medical Document",
        },
        "subject": {
            "reference": f"Patient/{doc.patient_id}",
        },
        "date": doc.created_at.isoformat() if doc.created_at else _utcnow_iso(),
        "description": doc.summary or f"{doc.document_type} - {doc.filename}",
        "content": [content_item],
    }

    if doc.model_used:
        resource.setdefault("extension", []).append(
            {
                "url": "http://hl7.org/fhir/StructureDefinition/ai-model-used",
                "valueString": doc.model_used,
            }
        )

    return resource


def diagnosis_to_fhir(diag: DiagnosisRecord) -> dict[str, Any]:
    """Convert DiagnosisRecord ORM model to a FHIR R4 Condition resource."""
    status_text = (diag.status or "").lower()
    clinical_code = (
        "resolved"
        if "resolved" in status_text or "inactive" in status_text
        else "active"
    )
    verification_code = (
        "provisional"
        if "provisional" in status_text or "suspected" in status_text
        else "confirmed"
    )

    resource: dict[str, Any] = {
        "resourceType": "Condition",
        "id": diag.id,
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": clinical_code,
                    "display": clinical_code.capitalize(),
                }
            ],
            "text": diag.status or clinical_code,
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": verification_code,
                    "display": verification_code.capitalize(),
                }
            ]
        },
        "code": {
            "text": diag.diagnosis,
        },
        "subject": {
            "reference": f"Patient/{diag.patient_id}",
        },
        "recordedDate": diag.created_at.isoformat() if diag.created_at else _utcnow_iso(),
    }

    evidence_item: dict[str, Any] = {
        "detail": [
            {
                "reference": f"DocumentReference/{diag.document_id}",
            }
        ]
    }
    if diag.evidence:
        evidence_item["code"] = [{"text": diag.evidence}]
    resource["evidence"] = [evidence_item]

    if diag.page_number:
        resource.setdefault("extension", []).append(
            {
                "url": "http://hl7.org/fhir/StructureDefinition/source-page-number",
                "valueInteger": diag.page_number,
            }
        )

    return resource


def medication_to_fhir(med: MedicationRecord) -> dict[str, Any]:
    """Convert MedicationRecord ORM model to a FHIR R4 MedicationStatement resource."""
    dosage_text_parts = [
        med.dose,
        med.frequency,
        f"for {med.duration}" if med.duration else None,
        f"via {med.route}" if med.route else None,
    ]
    dosage_text = " ".join([p for p in dosage_text_parts if p]).strip()

    dosage_entry: dict[str, Any] = {}
    if dosage_text:
        dosage_entry["text"] = dosage_text
    if med.instructions:
        dosage_entry["patientInstruction"] = med.instructions

    resource: dict[str, Any] = {
        "resourceType": "MedicationStatement",
        "id": med.id,
        "status": "active",
        "medicationCodeableConcept": {
            "text": med.name,
        },
        "subject": {
            "reference": f"Patient/{med.patient_id}",
        },
        "derivedFrom": [
            {
                "reference": f"DocumentReference/{med.document_id}",
            }
        ],
        "effectiveDateTime": med.created_at.isoformat() if med.created_at else _utcnow_iso(),
    }

    if dosage_entry:
        resource["dosage"] = [dosage_entry]

    if med.evidence:
        resource["note"] = [{"text": f"Evidence snippet: {med.evidence}"}]

    return resource


def lab_result_to_fhir(lab: LabResultRecord) -> dict[str, Any]:
    """Convert LabResultRecord ORM model to a FHIR R4 Observation resource."""
    resource: dict[str, Any] = {
        "resourceType": "Observation",
        "id": lab.id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "laboratory",
                        "display": "Laboratory",
                    }
                ],
                "text": "Laboratory",
            }
        ],
        "code": {
            "text": lab.test_name,
        },
        "subject": {
            "reference": f"Patient/{lab.patient_id}",
        },
        "derivedFrom": [
            {
                "reference": f"DocumentReference/{lab.document_id}",
            }
        ],
        "issued": lab.created_at.isoformat() if lab.created_at else _utcnow_iso(),
    }

    # Map value (numeric Quantity or String)
    numeric_val = _parse_numeric(lab.value)
    if numeric_val is not None:
        resource["valueQuantity"] = {
            "value": numeric_val,
            "unit": lab.unit or "",
        }
    elif lab.value:
        resource["valueString"] = lab.value

    # Reference range
    if lab.reference_range:
        resource["referenceRange"] = [
            {
                "text": lab.reference_range,
            }
        ]

    # Abnormal flag interpretation
    if lab.abnormal_flag is True:
        resource["interpretation"] = [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "A",
                        "display": "Abnormal",
                    }
                ],
                "text": "Abnormal / Out of Reference Range",
            }
        ]
    elif lab.abnormal_flag is False:
        resource["interpretation"] = [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "N",
                        "display": "Normal",
                    }
                ],
                "text": "Normal / Within Reference Range",
            }
        ]

    if lab.evidence:
        resource["note"] = [{"text": f"Source Evidence: {lab.evidence}"}]

    return resource


def build_fhir_bundle(
    resources: list[dict[str, Any]],
    bundle_id: str | None = None,
) -> dict[str, Any]:
    """Wrap FHIR resources into a valid FHIR R4 Bundle of type 'collection'."""
    bid = bundle_id or f"bundle-{uuid.uuid4()}"
    return {
        "resourceType": "Bundle",
        "id": bid,
        "meta": {
            "lastUpdated": _utcnow_iso(),
            "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"],
        },
        "type": "collection",
        "timestamp": _utcnow_iso(),
        "total": len(resources),
        "entry": [
            {
                "fullUrl": f"urn:uuid:{res['id']}",
                "resource": res,
            }
            for res in resources
        ],
    }


def export_patient_fhir_bundle(patient: Patient) -> dict[str, Any]:
    """Generate a complete FHIR R4 Bundle for a patient and all their clinical entities."""
    resources: list[dict[str, Any]] = [patient_to_fhir(patient)]

    for doc in patient.documents:
        resources.append(document_to_fhir(doc))

    for diag in patient.diagnoses:
        resources.append(diagnosis_to_fhir(diag))

    for med in patient.medications:
        resources.append(medication_to_fhir(med))

    for lab in patient.lab_results:
        resources.append(lab_result_to_fhir(lab))

    return build_fhir_bundle(resources, bundle_id=f"patient-{patient.id}-fhir-bundle")


def export_document_fhir_bundle(doc: MedicalDocument) -> dict[str, Any]:
    """Generate a FHIR R4 Bundle for a single medical document and its linked records."""
    resources: list[dict[str, Any]] = []

    if doc.patient:
        resources.append(patient_to_fhir(doc.patient))

    resources.append(document_to_fhir(doc))

    for diag in doc.diagnoses:
        resources.append(diagnosis_to_fhir(diag))

    for med in doc.medications:
        resources.append(medication_to_fhir(med))

    for lab in doc.lab_results:
        resources.append(lab_result_to_fhir(lab))

    return build_fhir_bundle(resources, bundle_id=f"doc-{doc.id}-fhir-bundle")
