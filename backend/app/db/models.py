"""SQLAlchemy 2.x ORM models for Personal Health Copilot persistence.

Defines schemas for:
- Patients (profiles)
- MedicalDocuments (persisted files, extraction metadata, raw text, and AI JSON snapshot)
- DiagnosisRecord (normalized relational clinical findings with evidence quotes and page numbers)
- MedicationRecord (normalized prescribed medications with exact dosage, frequency, and duration)
- LabResultRecord (normalized lab investigations with test name, value, unit, reference range, abnormal flag)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Authenticated user account for SaaS access and data ownership."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    patients: Mapped[list[Patient]] = relationship(
        "Patient",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="asc(Patient.created_at)",
    )


class Patient(Base):
    """Patient profile record."""

    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    user: Mapped[User | None] = relationship("User", back_populates="patients")
    documents: Mapped[list[MedicalDocument]] = relationship(
        "MedicalDocument",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(MedicalDocument.created_at)",
    )
    diagnoses: Mapped[list[DiagnosisRecord]] = relationship(
        "DiagnosisRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    medications: Mapped[list[MedicationRecord]] = relationship(
        "MedicationRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    lab_results: Mapped[list[LabResultRecord]] = relationship(
        "LabResultRecord",
        back_populates="patient",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list[ChatConversation]] = relationship(
        "ChatConversation",
        back_populates="patient",
        cascade="all, delete-orphan",
        order_by="desc(ChatConversation.updated_at)",
    )


class MedicalDocument(Base):
    """Persisted medical document record."""

    __tablename__ = "medical_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default="Other"
    )
    upload_date: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    processing_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="analyzed"
    )
    ai_analysis_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="success"
    )
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_char_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    extraction_method: Mapped[str] = mapped_column(
        String(50), nullable=False, default="selectable"
    )
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confidence_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="AI-extracted medical information. Always verify against original clinical documents.",
    )
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_extraction_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    patient: Mapped[Patient] = relationship("Patient", back_populates="documents")
    diagnoses: Mapped[list[DiagnosisRecord]] = relationship(
        "DiagnosisRecord",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    medications: Mapped[list[MedicationRecord]] = relationship(
        "MedicationRecord",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    lab_results: Mapped[list[LabResultRecord]] = relationship(
        "LabResultRecord",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DiagnosisRecord(Base):
    """Normalized diagnosis entity extracted from a medical document."""

    __tablename__ = "diagnoses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diagnosis: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    document: Mapped[MedicalDocument] = relationship(
        "MedicalDocument", back_populates="diagnoses"
    )
    patient: Mapped[Patient] = relationship(
        "Patient", back_populates="diagnoses"
    )


class MedicationRecord(Base):
    """Normalized medication entity extracted from a medical document."""

    __tablename__ = "medications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instructions: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    document: Mapped[MedicalDocument] = relationship(
        "MedicalDocument", back_populates="medications"
    )
    patient: Mapped[Patient] = relationship(
        "Patient", back_populates="medications"
    )


class LabResultRecord(Base):
    """Normalized laboratory investigation entity extracted from a medical document."""

    __tablename__ = "lab_results"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("medical_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    value: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_range: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    abnormal_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    document: Mapped[MedicalDocument] = relationship(
        "MedicalDocument", back_populates="lab_results"
    )
    patient: Mapped[Patient] = relationship(
        "Patient", back_populates="lab_results"
    )


class ChatConversation(Base):
    """Persistent chat conversation session for a patient."""

    __tablename__ = "chat_conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    patient_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, default="Health Consultation"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False, index=True
    )

    # Relationships
    patient: Mapped[Patient] = relationship(
        "Patient", back_populates="conversations"
    )
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="asc(ChatMessage.created_at)",
    )


class ChatMessage(Base):
    """Individual message within a persistent chat conversation."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_new_id
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False  # "user", "assistant", "system"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    model_used: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False, index=True
    )

    # Relationships
    conversation: Mapped[ChatConversation] = relationship(
        "ChatConversation", back_populates="messages"
    )

