from datetime import datetime, timezone
import logging
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from ..core.security import hash_password
from .base import Base
from .models import Patient, User
from .session import get_engine, get_session_factory

logger = logging.getLogger(__name__)

DEFAULT_DEMO_USER_ID = "demo-user-sunita-rao"
DEFAULT_DEMO_USER_EMAIL = "demo@healthcopilot.local"
DEFAULT_DEMO_USER_PASSWORD = "Demo@2026"
DEFAULT_DEMO_USER_NAME = "Sunita Rao"

DEFAULT_DEMO_PATIENT_ID = "demo-patient-sunita-rao"
DEFAULT_DEMO_PATIENT_NAME = "Smt. Sunita Rao"


def init_database(engine: Engine | None = None) -> None:
    """Create all tables and seed initial demo user and patient if empty."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)

    factory = get_session_factory(eng)
    with factory() as db:
        demo_user = get_or_create_default_user(db)
        get_or_create_default_patient(db, user_id=demo_user.id)

        # Ensure any legacy or orphaned patients without user_id are safely linked to demo_user
        orphaned = db.scalars(select(Patient).where(Patient.user_id.is_(None))).all()
        for p in orphaned:
            p.user_id = demo_user.id
        if orphaned:
            db.commit()


def get_or_create_default_user(db: Session) -> User:
    """Ensure the default demo user exists for evaluation, testing, and 1-click login."""
    user = db.scalar(select(User).where(User.email == DEFAULT_DEMO_USER_EMAIL))
    if user:
        return user

    logger.info("Seeding initial demo user: %s", DEFAULT_DEMO_USER_EMAIL)
    now = datetime.now(timezone.utc)
    demo_user = User(
        id=DEFAULT_DEMO_USER_ID,
        email=DEFAULT_DEMO_USER_EMAIL,
        hashed_password=hash_password(DEFAULT_DEMO_USER_PASSWORD),
        full_name=DEFAULT_DEMO_USER_NAME,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    return demo_user


def get_or_create_default_patient(db: Session, user_id: str | None = None) -> Patient:
    """Ensure the default fictional Indian patient profile exists and is linked to the demo user."""
    stmt = select(Patient).where(Patient.id == DEFAULT_DEMO_PATIENT_ID)
    patient = db.scalars(stmt).first()
    if patient:
        if user_id and not patient.user_id:
            patient.user_id = user_id
            db.commit()
            db.refresh(patient)
        return patient

    # If another patient exists, check if any exists
    first_patient = db.scalars(select(Patient).limit(1)).first()
    if first_patient:
        if user_id and not first_patient.user_id:
            first_patient.user_id = user_id
            db.commit()
            db.refresh(first_patient)
        return first_patient

    logger.info("Seeding initial fictional patient: %s", DEFAULT_DEMO_PATIENT_NAME)
    demo_patient = Patient(
        id=DEFAULT_DEMO_PATIENT_ID,
        user_id=user_id,
        display_name=DEFAULT_DEMO_PATIENT_NAME,
        age="52 Yrs",
        gender="Female",
    )
    db.add(demo_patient)
    db.commit()
    db.refresh(demo_patient)
    return demo_patient
