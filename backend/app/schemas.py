"""Pydantic response models for the PDF extraction endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PageText(BaseModel):
    """Extracted text for a single PDF page."""

    page_number: int = Field(..., description="1-based page number within the PDF.")
    text: str = Field(..., description="Text extracted from this page.")
    char_count: int = Field(..., description="Number of characters extracted from this page.")
    method: str = Field(
        "selectable",
        description="How the text was obtained: 'selectable' (PDF text layer) or 'ocr'.",
    )


class PdfTextExtractionResponse(BaseModel):
    """Successful PDF text extraction result.

    The extracted text is returned page-by-page so callers can navigate the
    document. ``full_text`` concatenates all pages in order.
    """

    page_count: int = Field(..., description="Total number of pages in the PDF.")
    pages: list[PageText] = Field(..., description="Text extracted per page.")
    full_text: str = Field(..., description="Concatenation of all page texts.")
    total_char_count: int = Field(..., description="Total extracted characters across all pages.")
    has_selectable_text: bool = Field(
        ...,
        description="True when at least one page contained extractable text.",
    )
    note: str = Field(
        ...,
        description="Human-readable note about the extraction result and any limitations.",
    )


class PdfTextExtractionError(BaseModel):
    """Error response for PDF extraction failures."""

    error: Literal[
        "file_too_large",
        "unsupported_file_type",
        "invalid_pdf",
        "encrypted_pdf",
        "empty_document",
        "no_text_extracted",
        "extraction_failed",
        "ocr_unavailable",
        "too_many_pages",
    ]
    message: str


class OcrTextExtractionResponse(BaseModel):
    """Successful OCR text extraction result.

    Returned for image files (JPEG/PNG) and scanned PDFs processed with
    Tesseract. ``page_count`` is 1 for single images.
    """

    page_count: int = Field(..., description="Total number of pages/images processed.")
    pages: list[PageText] = Field(..., description="OCR text extracted per page.")
    full_text: str = Field(..., description="Concatenation of all page texts.")
    total_char_count: int = Field(..., description="Total extracted characters across all pages.")
    has_text: bool = Field(
        ...,
        description="True when at least one page contained recognized text.",
    )
    ocr_engine: str = Field(..., description="OCR engine used (e.g. 'tesseract').")
    ocr_languages: list[str] = Field(
        ...,
        description="Tesseract language codes used for recognition.",
    )
    note: str = Field(
        ...,
        description="Human-readable note about the OCR result and limitations.",
    )


class DiagnosisItem(BaseModel):
    """A diagnosis explicitly documented in the medical document."""

    diagnosis: str = Field(
        ...,
        description="Condition or diagnosis explicitly stated in the source text.",
    )
    status: str | None = Field(
        None,
        description="Status if stated (e.g. 'confirmed', 'provisional', 'suspected', 'resolved').",
    )
    evidence: str | None = Field(
        None,
        description="Exact snippet or quote from the source text supporting this diagnosis.",
    )
    page_number: int | None = Field(
        None,
        description="Source page number where this diagnosis was found, if available.",
    )


class MedicationItem(BaseModel):
    """A medication explicitly prescribed or recorded in the source."""

    name: str = Field(
        ...,
        description="Exact medication name as written in the source (e.g. 'Tab. Metformin').",
    )
    dose: str | None = Field(
        None,
        description="Exact dosage as written (e.g. '500 mg', '10 ml'), or null if not stated.",
    )
    frequency: str | None = Field(
        None,
        description="Frequency as written (e.g. '1-0-1', 'twice daily', 'OD', 'TDS'), or null if not stated.",
    )
    duration: str | None = Field(
        None,
        description="Duration as written (e.g. '5 days', '1 month', 'SOS'), or null if not stated.",
    )
    route: str | None = Field(
        None,
        description="Route of administration if written (e.g. 'oral', 'topical', 'IV'), or null if not stated.",
    )
    instructions: str | None = Field(
        None,
        description="Additional instructions as written (e.g. 'after meals', 'at bedtime'), or null if not stated.",
    )
    evidence: str | None = Field(
        None,
        description="Source snippet or quote where this medication was found.",
    )
    page_number: int | None = Field(
        None,
        description="Source page number, if available.",
    )


class LabTestItem(BaseModel):
    """A laboratory or diagnostic test result explicitly supported by the source."""

    test_name: str = Field(
        ...,
        description="Exact name of the test as written in the source (e.g. 'Fasting Blood Sugar').",
    )
    value: str | None = Field(
        None,
        description="Reported value or result as written (e.g. '142', 'Negative', 'Not detected').",
    )
    unit: str | None = Field(
        None,
        description="Measurement unit (e.g. 'mg/dL', 'g/dL'), or null if not stated.",
    )
    reference_range: str | None = Field(
        None,
        description="Reference interval as written (e.g. '70 - 99 mg/dL'), or null if not provided.",
    )
    abnormal_flag: bool | None = Field(
        None,
        description="True if explicitly marked abnormal/high/low in source, False if normal, null if not indicated.",
    )
    evidence: str | None = Field(
        None,
        description="Source snippet or quote where this test result was found.",
    )
    page_number: int | None = Field(
        None,
        description="Source page number, if available.",
    )


class MedicalDocumentExtraction(BaseModel):
    """Structured extraction of medical document data validated with Pydantic."""

    document_type: str | None = Field(
        None,
        description="Document type if present (e.g. 'Lab report', 'Prescription', 'Discharge summary'), or null if not mentioned.",
    )
    report_date: str | None = Field(
        None,
        description="Report or consultation date explicitly stated in the source, or null if not mentioned.",
    )
    patient_name: str | None = Field(
        None,
        description="Patient name ONLY if explicitly present in the source; null if not mentioned.",
    )
    patient_age: str | None = Field(
        None,
        description="Patient age if explicitly stated in the source, or null if not mentioned.",
    )
    patient_gender: str | None = Field(
        None,
        description="Patient gender/sex if explicitly stated in the source, or null if not mentioned.",
    )
    diagnoses: list[DiagnosisItem] = Field(
        default_factory=list,
        description="Diagnoses explicitly documented in the source. Never inferred from lab results.",
    )
    medicines: list[MedicationItem] = Field(
        default_factory=list,
        description="Medicines with exact name, dose, frequency, and duration as written.",
    )
    lab_tests: list[LabTestItem] = Field(
        default_factory=list,
        description="Lab test name, value, unit, reference range, and abnormal flag only when supported.",
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Medical fields expected for this record type that are not mentioned in the source.",
    )
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Ambiguities, illegible words, or OCR errors identified in the source text.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        "high",
        description="Extraction confidence based on text clarity and completeness.",
    )
    confidence_reason: str | None = Field(
        None,
        description="Brief explanation for the extraction confidence assessment.",
    )
    summary: str | None = Field(
        None,
        description="Neutral, objective summary of the document without medical advice or diagnoses not in the source.",
    )
    disclaimer: str = Field(
        "AI-extracted medical information. Always verify against original clinical documents. Not a medical diagnosis or clinical recommendation.",
        description="Visible safety warning regarding AI extraction.",
    )
    model_used: str = Field(
        "gemini-3.1-flash-lite",
        description="Gemini model used for this extraction.",
    )


class AnalyzeDocumentRequest(BaseModel):
    """Payload sent to /api/documents/analyze-ai."""

    text: str = Field(
        ...,
        description="Extracted text from PDF selectable layers or OCR to analyze with Gemini.",
    )
    pages: list[PageText] | None = Field(
        None,
        description="Optional page-by-page breakdown of text.",
    )
    document_type_hint: str | None = Field(
        None,
        description="Optional hint for document type (e.g. 'Lab report', 'Prescription').",
    )


class AnalyzeDocumentError(BaseModel):
    """Error response for document analysis failures."""

    error: Literal[
        "api_key_missing",
        "empty_text",
        "text_too_large",
        "rate_limit_exceeded",
        "api_error",
        "invalid_output",
        "service_unavailable",
    ]
    message: str


# ============================================================================
# Persistence Schemas (Step 6)
# ============================================================================


class PatientCreate(BaseModel):
    """Payload to create a new patient profile."""

    display_name: str = Field(..., min_length=1, max_length=255, description="Full display name of patient")
    age: str | None = Field(None, max_length=50, description="Age (e.g. '52')")
    gender: str | None = Field(None, max_length=50, description="Gender (e.g. 'Female', 'Male')")


class PatientResponse(BaseModel):
    """Patient profile response."""

    id: str
    display_name: str
    age: str | None = None
    gender: str | None = None
    document_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    """List of patient profiles."""

    patients: list[PatientResponse]
    total: int


class DiagnosisRecordResponse(BaseModel):
    id: str
    document_id: str
    patient_id: str
    diagnosis: str
    status: str | None = None
    evidence: str | None = None
    page_number: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicationRecordResponse(BaseModel):
    id: str
    document_id: str
    patient_id: str
    name: str
    dose: str | None = None
    frequency: str | None = None
    duration: str | None = None
    route: str | None = None
    instructions: str | None = None
    evidence: str | None = None
    page_number: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LabResultRecordResponse(BaseModel):
    id: str
    document_id: str
    patient_id: str
    test_name: str
    value: str | None = None
    unit: str | None = None
    reference_range: str | None = None
    abnormal_flag: bool | None = None
    evidence: str | None = None
    page_number: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SaveDocumentRequest(BaseModel):
    """Request payload to persist an extracted document and structured records."""

    patient_id: str = Field(..., description="Target patient UUID")
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    document_type: str = Field("Other", max_length=100, description="Document classification")
    upload_date: str | None = Field(None, description="Date of document or upload (YYYY-MM-DD)")
    processing_status: str = Field("analyzed", max_length=50)
    ai_analysis_status: str = Field("success", max_length=50)
    page_count: int = Field(1, ge=1)
    total_char_count: int = Field(0, ge=0)
    extraction_method: str = Field("selectable", max_length=50)
    confidence: str | None = Field(None, max_length=20)
    confidence_reason: str | None = None
    summary: str | None = None
    disclaimer: str = Field(
        "AI-extracted medical information. Always verify against original clinical documents.",
        description="Clinical safety disclaimer",
    )
    model_used: str | None = None
    raw_text: str | None = Field(None, description="Verifiable extracted raw text from PDF/OCR")
    ai_extraction: MedicalDocumentExtraction | None = Field(
        None, description="Full validated AI extraction payload snapshot"
    )
    custom_diagnoses: list[DiagnosisItem] | None = None
    custom_medications: list[MedicationItem] | None = None
    custom_lab_results: list[LabTestItem] | None = None


class UpdateDocumentRequest(BaseModel):
    """Payload to update document metadata."""

    filename: str | None = Field(None, min_length=1, max_length=255)
    document_type: str | None = Field(None, min_length=1, max_length=100)
    summary: str | None = None


class SavedDocumentSummary(BaseModel):
    """Summary of a persisted document."""

    id: str
    patient_id: str
    filename: str
    document_type: str
    upload_date: str
    processing_status: str
    ai_analysis_status: str
    page_count: int
    total_char_count: int
    extraction_method: str
    confidence: str | None = None
    confidence_reason: str | None = None
    summary: str | None = None
    disclaimer: str
    model_used: str | None = None
    created_at: datetime
    updated_at: datetime
    diagnoses_count: int = 0
    medications_count: int = 0
    lab_results_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SavedDocumentDetail(SavedDocumentSummary):
    """Full detail of a persisted document including structured records and raw text."""

    raw_text: str | None = None
    ai_extraction_json: dict[str, Any] | None = None
    diagnoses: list[DiagnosisRecordResponse] = []
    medications: list[MedicationRecordResponse] = []
    lab_results: list[LabResultRecordResponse] = []


class SavedDocumentListResponse(BaseModel):
    documents: list[SavedDocumentSummary]
    total: int


# ============================================================================
# Telugu Summary Schemas (Step 7)
# ============================================================================


class TeluguDiagnosisExplanation(BaseModel):
    """Telugu patient-friendly explanation for a clinical diagnosis."""

    original_diagnosis: str = Field(..., description="Exact English diagnosis as written in document")
    diagnosis: str | None = Field(None, description="Exact English diagnosis (alias for frontend)")
    telugu_term: str | None = Field(None, description="Telugu name or transliteration of the diagnosis")
    telugu_explanation: str = Field(..., description="Patient-friendly explanation in clear Telugu script")
    status: str | None = None
    evidence: str | None = None

    @model_validator(mode="after")
    def populate_diagnosis_aliases(self) -> TeluguDiagnosisExplanation:
        if not self.diagnosis:
            self.diagnosis = self.original_diagnosis
        if not self.telugu_term:
            self.telugu_term = self.original_diagnosis
        return self


class TeluguMedicineExplanation(BaseModel):
    """Telugu patient-friendly explanation for a prescribed medication."""

    name: str = Field(..., description="Exact medicine name preserved from source")
    dose: str | None = Field(None, description="Exact dose preserved (e.g. '500 mg')")
    frequency: str | None = Field(None, description="Exact frequency preserved (e.g. '1-0-1')")
    duration: str | None = Field(None, description="Exact duration preserved (e.g. '30 days')")
    instructions: str | None = None
    telugu_purpose_and_instructions: str = Field(
        ...,
        description="Patient-friendly Telugu explanation of purpose and administration as documented",
    )


class TeluguLabExplanation(BaseModel):
    """Telugu patient-friendly explanation for a laboratory investigation."""

    test_name: str = Field(..., description="Exact lab test name preserved")
    value: str | None = Field(None, description="Exact value preserved")
    unit: str | None = Field(None, description="Exact measurement unit preserved")
    reference_range: str | None = Field(None, description="Exact reference range preserved")
    abnormal_flag: bool | None = Field(None, description="Abnormal flag indicator")
    telugu_explanation: str | None = Field(
        None,
        description="Patient-friendly Telugu explanation of what the test indicates in plain language",
    )
    telugu_status_and_meaning: str | None = Field(
        None,
        description="Patient-friendly Telugu explanation of test status and meaning",
    )

    @model_validator(mode="after")
    def populate_lab_meaning(self) -> TeluguLabExplanation:
        if not self.telugu_status_and_meaning and self.telugu_explanation:
            self.telugu_status_and_meaning = self.telugu_explanation
        elif not self.telugu_explanation and self.telugu_status_and_meaning:
            self.telugu_explanation = self.telugu_status_and_meaning
        elif not self.telugu_status_and_meaning and not self.telugu_explanation:
            meaning = f"{self.test_name} ఫలితం: {self.value or ''} {self.unit or ''}"
            self.telugu_status_and_meaning = meaning
            self.telugu_explanation = meaning
        return self


class TeluguHealthSummary(BaseModel):
    """Comprehensive patient-friendly Telugu explanation of a medical document."""

    overall_summary_telugu: str = Field(..., description="Overall document summary in clear Telugu script")
    diagnoses_explanations: list[TeluguDiagnosisExplanation] = Field(default_factory=list)
    medicines_explanations: list[TeluguMedicineExplanation] = Field(default_factory=list)
    labs_explanations: list[TeluguLabExplanation] = Field(default_factory=list)
    disclaimer_telugu: str = Field(
        "ఈ సమాచారం కేవలం రోగి అవగాహన కొరకు మాత్రమే. ఇది వైద్య నిర్ధారణ లేదా చికిత్స సలహా కాదు. ఎల్లప్పుడూ మీ వైద్యుడిని సంప్రదించండి.",
        description="Mandatory Telugu medical safety disclaimer",
    )
    model_used: str = Field("gemini-3.1-flash-lite", description="Gemini model used for explanation")


class TeluguExplainRequest(BaseModel):
    """Payload to request a Telugu explanation from a validated extraction."""

    extraction: MedicalDocumentExtraction | None = None
    text: str | None = None
    document_type_hint: str | None = None


# ============================================================================
# Persistent Health AI Chat Schemas (Step 9)
# ============================================================================


class ChatCitationItem(BaseModel):
    """Grounding citation referencing a specific medical document or lab result."""

    document_id: str = Field(..., description="ID of the referenced document")
    document_name: str = Field(..., description="Filename or title of document")
    report_date: str | None = Field(None, description="Date of document or encounter")
    entity_type: str = Field(..., description="'diagnosis', 'medication', 'lab_result', or 'report_summary'")
    entity_text: str = Field(..., description="Quoted or referenced fact from medical record")
    value: str | None = Field(None, description="Test value or dosage if applicable")
    unit: str | None = Field(None, description="Measurement unit if applicable")
    reference_range: str | None = Field(None, description="Standard reference range if applicable")


class ChatMessageResponse(BaseModel):
    """Individual chat message response."""

    id: str
    conversation_id: str
    role: str  # "user", "assistant", "system"
    content: str
    citations: list[ChatCitationItem] | None = None
    model_used: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatConversationSummary(BaseModel):
    """Conversation summary item for listing patient sessions."""

    id: str
    patient_id: str
    title: str
    message_count: int = 0
    last_message_preview: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatConversationDetail(BaseModel):
    """Full conversation with ordered message history."""

    id: str
    patient_id: str
    title: str
    messages: list[ChatMessageResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatConversationCreate(BaseModel):
    """Payload to create a new conversation."""

    title: str | None = Field(None, max_length=255, description="Optional title for the conversation")


class ChatSendMessageRequest(BaseModel):
    """Payload to send a message in a conversation or initiate a chat."""

    message: str = Field(..., min_length=1, max_length=5000, description="Patient's query or message")
    conversation_id: str | None = Field(None, description="Existing conversation ID or None to start new")


class ChatSendMessageResponse(BaseModel):
    """Response returned after sending a chat message."""

    conversation_id: str
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    suggested_follow_ups: list[str] = Field(default_factory=list)


class HealthCopilotAiReply(BaseModel):
    """Structured AI output from Gemini for Personal Health Copilot chat."""

    answer_markdown: str = Field(
        ...,
        description="Compassionate, personalized, markdown-formatted response based strictly on patient records.",
    )
    citations: list[ChatCitationItem] = Field(
        default_factory=list,
        description="Citations to verified patient documents, dates, and test values used in the answer.",
    )
    suggested_follow_ups: list[str] = Field(
        default_factory=list,
        description="2 to 3 contextual follow-up questions the patient might want to ask.",
    )
    model_used: str | None = Field(
        default=None,
        description="The actual model used to generate this response.",
    )


# ============================================================================
# User Authentication Schemas (SaaS)
# ============================================================================


class UserRegisterRequest(BaseModel):
    """Payload to register a new user account."""

    email: str = Field(
        ...,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="User's email address",
    )
    password: str = Field(..., min_length=8, max_length=128, description="Password (at least 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=255, description="User's full name")


class UserLoginRequest(BaseModel):
    """Payload to log into an existing user account."""

    email: str = Field(
        ...,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        description="Registered email address",
    )
    password: str = Field(..., min_length=1, max_length=128, description="Account password")


class UserResponse(BaseModel):
    """Public user profile response."""

    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT bearer token and user summary."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


