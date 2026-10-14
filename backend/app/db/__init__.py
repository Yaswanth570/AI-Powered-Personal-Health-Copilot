"""Database module."""

from .base import Base
from .init_db import (
    DEFAULT_DEMO_PATIENT_ID,
    DEFAULT_DEMO_PATIENT_NAME,
    get_or_create_default_patient,
    init_database,
)
from .models import (
    DiagnosisRecord,
    LabResultRecord,
    MedicalDocument,
    MedicationRecord,
    Patient,
)
from .session import get_db, get_engine, get_session_factory, normalize_database_url

__all__ = [
    "Base",
    "Patient",
    "MedicalDocument",
    "DiagnosisRecord",
    "MedicationRecord",
    "LabResultRecord",
    "get_db",
    "get_engine",
    "get_session_factory",
    "normalize_database_url",
    "init_database",
    "get_or_create_default_patient",
    "DEFAULT_DEMO_PATIENT_ID",
    "DEFAULT_DEMO_PATIENT_NAME",
]
