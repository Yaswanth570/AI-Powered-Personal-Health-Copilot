"""Database initialization and fictional Indian demo seeding."""

from __future__ import annotations

import logging
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .base import Base
from .models import Patient
from .session import get_engine, get_session_factory

logger = logging.getLogger(__name__)

DEFAULT_DEMO_PATIENT_ID = "demo-patient-sunita-rao"
DEFAULT_DEMO_PATIENT_NAME = "Smt. Sunita Rao"


def init_database(engine: Engine | None = None) -> None:
    """Create all tables and seed initial demo patient if empty."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)

    factory = get_session_factory(eng)
    with factory() as db:
        get_or_create_default_patient(db)


def get_or_create_default_patient(db: Session) -> Patient:
    """Ensure the default fictional Indian patient profile exists."""
    stmt = select(Patient).where(Patient.id == DEFAULT_DEMO_PATIENT_ID)
    patient = db.scalars(stmt).first()
    if patient:
        return patient

    # If another patient exists, check if any exists
    first_patient = db.scalars(select(Patient).limit(1)).first()
    if first_patient:
        return first_patient

    logger.info("Seeding initial fictional patient: %s", DEFAULT_DEMO_PATIENT_NAME)
    demo_patient = Patient(
        id=DEFAULT_DEMO_PATIENT_ID,
        display_name=DEFAULT_DEMO_PATIENT_NAME,
        age="52 Yrs",
        gender="Female",
    )
    db.add(demo_patient)
    db.commit()
    db.refresh(demo_patient)
    return demo_patient
