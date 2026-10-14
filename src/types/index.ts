export type NavSection =
  | "overview"
  | "health-ai"
  | "records"
  | "labs"
  | "prescriptions"
  | "timeline"
  | "settings";

export type DocumentType =
  | "Lab report"
  | "Imaging summary"
  | "Visit note"
  | "Prescription"
  | "Discharge summary"
  | "Diagnostic report"
  | "Other";

export type UploadDocumentType =
  | "Lab report"
  | "Prescription"
  | "Diagnostic report"
  | "Discharge summary"
  | "Other";

export type RecordOrigin = "demo" | "session" | "database";

export type RecordStatus =
  | "Queued (demo)"
  | "Ready to review (demo)"
  | "Listed (demo)"
  | "Uploaded — analysis not yet available"
  | "Saving to Database..."
  | "Saved in Database";

export interface MedicalRecord {
  id: string;
  name: string;
  type: DocumentType;
  uploadedOn: string;
  status: RecordStatus;
  sourceNote: string;
  origin: RecordOrigin;
  fileSizeLabel?: string;
  /** Browser-memory File for this session only. Never persisted. */
  file?: File;
  /** Persisted document detail from PostgreSQL, if saved. */
  persistedDoc?: SavedMedicalDocument;
  persistedId?: string;
}

export interface SummaryCard {
  id: string;
  label: string;
  value: string;
  detail: string;
  icon: "folder" | "flask" | "pill" | "calendar";
}

export interface LabInsight {
  testName: string;
  panelName: string;
  value: string;
  unit: string;
  sampleReferenceRange: string;
  statusLabel: string;
  educationalNote: string;
}

export interface TimelineEvent {
  id: string;
  date: string;
  title: string;
  documentType: DocumentType;
  summary: string;
}

export interface PrescriptionItem {
  id: string;
  name: string;
  sampleSig: string;
  clinic: string;
  listedOn: string;
}

export interface DemoNotification {
  id: string;
  title: string;
  body: string;
  time: string;
}

export interface NavItem {
  id: NavSection;
  label: string;
}

/** One page of text extracted from a PDF. */
export interface ExtractedPage {
  page_number: number;
  text: string;
  char_count: number;
  method: "selectable" | "ocr";
}

/** Successful PDF text extraction response from the backend. */
export interface PdfExtractionResult {
  page_count: number;
  pages: ExtractedPage[];
  full_text: string;
  total_char_count: number;
  has_selectable_text: boolean;
  note: string;
}

/** Successful OCR text extraction response (images + scanned PDFs). */
export interface OcrExtractionResult {
  page_count: number;
  pages: ExtractedPage[];
  full_text: string;
  total_char_count: number;
  has_text: boolean;
  ocr_engine: string;
  ocr_languages: string[];
  note: string;
}

/** Error response from the PDF extraction endpoint. */
export interface PdfExtractionError {
  error:
    | "file_too_large"
    | "unsupported_file_type"
    | "invalid_pdf"
    | "encrypted_pdf"
    | "empty_document"
    | "no_text_extracted"
    | "extraction_failed"
    | "ocr_unavailable"
    | "too_many_pages";
  message: string;
}

/** Lifecycle of an extraction request for a single session document. */
export type ExtractionStatus = "idle" | "loading" | "success" | "error";

/** Diagnosis explicitly extracted from medical text. */
export interface DiagnosisItem {
  diagnosis: string;
  status: string | null;
  evidence: string | null;
  page_number: number | null;
}

/** Medication extracted with exact name, dose, frequency, and duration. */
export interface MedicationItem {
  name: string;
  dose: string | null;
  frequency: string | null;
  duration: string | null;
  route: string | null;
  instructions: string | null;
  evidence: string | null;
  page_number: number | null;
}

/** Lab test result extracted with value, unit, reference range, and flag. */
export interface LabTestItem {
  test_name: string;
  value: string | null;
  unit: string | null;
  reference_range: string | null;
  abnormal_flag: boolean | null;
  evidence: string | null;
  page_number: number | null;
}

/** Validated Gemini AI structured extraction result. */
export interface MedicalDocumentExtraction {
  document_type: string | null;
  report_date: string | null;
  patient_name: string | null;
  patient_age: string | null;
  patient_gender: string | null;
  diagnoses: DiagnosisItem[];
  medicines: MedicationItem[];
  lab_tests: LabTestItem[];
  missing_fields: string[];
  uncertainties: string[];
  confidence: "high" | "medium" | "low";
  confidence_reason: string | null;
  summary: string | null;
  disclaimer: string;
  model_used: string;
}

/** Error response from the AI analysis endpoint. */
export interface AnalyzeDocumentError {
  error:
    | "api_key_missing"
    | "empty_text"
    | "text_too_large"
    | "rate_limit_exceeded"
    | "api_error"
    | "invalid_output"
    | "service_unavailable";
  message: string;
}

/** Lifecycle of an AI analysis request for a session document. */
export type AiAnalysisStatus = "idle" | "loading" | "success" | "error";

export interface AiAnalysisState {
  status: AiAnalysisStatus;
  result?: MedicalDocumentExtraction;
  errorMessage?: string;
}

/** Patient profile persisted in PostgreSQL. */
export interface PatientRecord {
  id: string;
  display_name: string;
  age: string | null;
  gender: string | null;
  document_count: number;
  created_at: string;
  updated_at: string;
}

/** Normalized diagnosis row in PostgreSQL. */
export interface SavedDiagnosisRecord {
  id: string;
  document_id: string;
  patient_id: string;
  diagnosis: string;
  status: string | null;
  evidence: string | null;
  page_number: number | null;
  created_at: string;
}

/** Normalized medication row in PostgreSQL. */
export interface SavedMedicationRecord {
  id: string;
  document_id: string;
  patient_id: string;
  name: string;
  dose: string | null;
  frequency: string | null;
  duration: string | null;
  route: string | null;
  instructions: string | null;
  evidence: string | null;
  page_number: number | null;
  created_at: string;
}

/** Normalized lab result row in PostgreSQL. */
export interface SavedLabResultRecord {
  id: string;
  document_id: string;
  patient_id: string;
  test_name: string;
  value: string | null;
  unit: string | null;
  reference_range: string | null;
  abnormal_flag: boolean | null;
  evidence: string | null;
  page_number: number | null;
  created_at: string;
}

/** Persisted medical document summary & full detail from PostgreSQL. */
export interface SavedMedicalDocument {
  id: string;
  patient_id: string;
  filename: string;
  document_type: DocumentType | string;
  upload_date: string;
  processing_status: string;
  ai_analysis_status: string;
  page_count: number;
  total_char_count: number;
  extraction_method: string;
  confidence: "high" | "medium" | "low" | null;
  confidence_reason: string | null;
  summary: string | null;
  disclaimer: string;
  model_used: string | null;
  created_at: string;
  updated_at: string;
  diagnoses_count: number;
  medications_count: number;
  lab_results_count: number;
  raw_text?: string | null;
  ai_extraction_json?: MedicalDocumentExtraction | null;
  diagnoses?: SavedDiagnosisRecord[];
  medications?: SavedMedicationRecord[];
  lab_results?: SavedLabResultRecord[];
}

/** Payload sent to /api/documents/save. */
export interface SaveDocumentPayload {
  patient_id: string;
  filename: string;
  document_type?: string;
  upload_date?: string;
  processing_status?: string;
  ai_analysis_status?: string;
  page_count?: number;
  total_char_count?: number;
  extraction_method?: string;
  confidence?: string | null;
  confidence_reason?: string | null;
  summary?: string | null;
  disclaimer?: string;
  model_used?: string | null;
  raw_text?: string | null;
  ai_extraction?: MedicalDocumentExtraction | null;
  custom_diagnoses?: DiagnosisItem[];
  custom_medications?: MedicationItem[];
  custom_lab_results?: LabTestItem[];
}

/** Structured Telugu health summary response from Gemini. */
export interface TeluguDiagnosisExplanation {
  original_diagnosis?: string;
  diagnosis?: string;
  telugu_term?: string;
  telugu_explanation: string;
}

export interface TeluguMedicineExplanation {
  name: string;
  dose: string | null;
  frequency: string | null;
  duration: string | null;
  telugu_purpose_and_instructions: string;
}

export interface TeluguLabExplanation {
  test_name: string;
  value: string | null;
  unit: string | null;
  reference_range: string | null;
  abnormal_flag: boolean | null;
  telugu_status_and_meaning?: string;
  telugu_explanation?: string;
}

export interface TeluguHealthSummary {
  overall_summary_telugu: string;
  diagnoses_explanations: TeluguDiagnosisExplanation[];
  medicines_explanations: TeluguMedicineExplanation[];
  labs_explanations: TeluguLabExplanation[];
  disclaimer_telugu: string;
  model_used: string;
}

/** HL7 FHIR R4 Resource representation. */
export interface FhirResource {
  resourceType: string;
  id: string;
  [key: string]: unknown;
}

/** HL7 FHIR R4 Bundle entry. */
export interface FhirBundleEntry {
  fullUrl: string;
  resource: FhirResource;
}

/** HL7 FHIR R4 Collection Bundle. */
export interface FhirBundle {
  resourceType: "Bundle";
  id: string;
  type: "collection";
  timestamp: string;
  total: number;
  entry: FhirBundleEntry[];
}

// ============================================================================
// Health AI Copilot Chat Interfaces (Step 9)
// ============================================================================

export interface ChatCitationItem {
  document_id: string;
  document_name: string;
  report_date?: string | null;
  entity_type: "diagnosis" | "medication" | "lab_result" | "report_summary" | string;
  entity_text: string;
  value?: string | null;
  unit?: string | null;
  reference_range?: string | null;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: ChatCitationItem[] | null;
  model_used?: string | null;
  created_at: string;
}

export interface ChatConversationSummary {
  id: string;
  patient_id: string;
  title: string;
  message_count: number;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatConversationDetail {
  id: string;
  patient_id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatSendMessageRequest {
  message: string;
  conversation_id?: string | null;
}

export interface ChatSendMessageResponse {
  conversation_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  suggested_follow_ups: string[];
}

// ============================================================================
// SaaS Authentication Interfaces (Phase 3)
// ============================================================================

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}



