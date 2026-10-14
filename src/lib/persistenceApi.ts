/** API Client for PostgreSQL persistence of patients and medical documents.
 *
 * Interacts with FastAPI backend endpoints:
 * - GET/POST /api/patients
 * - GET /api/patients/{id}
 * - GET/POST /api/documents
 * - POST /api/documents/save
 * - GET/PATCH/DELETE /api/documents/{id}
 */

import type {
  FhirBundle,
  MedicalDocumentExtraction,
  PatientRecord,
  SaveDocumentPayload,
  SavedMedicalDocument,
  TeluguHealthSummary,
} from "../types";
import { getApiBaseUrl } from "./pdfApi";

export class PersistenceApiError extends Error {
  public readonly status: number;
  public readonly details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "PersistenceApiError";
    this.status = status;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response, defaultMessage: string): Promise<T> {
  if (res.ok) {
    return (await res.json()) as T;
  }

  let errorDetail = defaultMessage;
  let rawJson: unknown;
  try {
    rawJson = await res.json();
    if (rawJson && typeof rawJson === "object" && "detail" in rawJson) {
      errorDetail = String((rawJson as { detail: unknown }).detail);
    }
  } catch {
    // response is not JSON
  }

  throw new PersistenceApiError(
    `${defaultMessage} (HTTP ${res.status}): ${errorDetail}`,
    res.status,
    rawJson,
  );
}

/** Fetch all patient profiles from the database. */
export async function fetchPatients(): Promise<PatientRecord[]> {
  const url = `${getApiBaseUrl()}/api/patients`;
  const res = await fetch(url, { method: "GET" });
  const data = await handleResponse<{ patients: PatientRecord[]; total: number }>(
    res,
    "Failed to load patient profiles",
  );
  return data.patients;
}

/** Create a new patient profile. */
export async function createPatient(
  displayName: string,
  age?: string,
  gender?: string,
): Promise<PatientRecord> {
  const url = `${getApiBaseUrl()}/api/patients`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      display_name: displayName,
      age: age || null,
      gender: gender || null,
    }),
  });
  return handleResponse<PatientRecord>(res, "Failed to create patient profile");
}

/** Fetch all saved documents from the database (optionally filtered by patient). */
export async function fetchSavedDocuments(
  patientId?: string,
): Promise<SavedMedicalDocument[]> {
  const params = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : "";
  const url = `${getApiBaseUrl()}/api/documents${params}`;
  const res = await fetch(url, { method: "GET" });
  const data = await handleResponse<{
    documents: SavedMedicalDocument[];
    total: number;
  }>(res, "Failed to load saved medical records");
  return data.documents;
}

/** Fetch full detail of a saved document including structured entities and raw text. */
export async function fetchDocumentDetail(
  documentId: string,
): Promise<SavedMedicalDocument> {
  const url = `${getApiBaseUrl()}/api/documents/${encodeURIComponent(documentId)}`;
  const res = await fetch(url, { method: "GET" });
  return handleResponse<SavedMedicalDocument>(
    res,
    `Failed to load document details for '${documentId}'`,
  );
}

/** Transactionally persist a medical document and its validated AI extraction. */
export async function saveDocumentToDatabase(
  payload: SaveDocumentPayload,
): Promise<SavedMedicalDocument> {
  const url = `${getApiBaseUrl()}/api/documents/save`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse<SavedMedicalDocument>(
    res,
    "Failed to persist document to database",
  );
}

/** Update document metadata (filename, document type, summary). */
export async function updateDocumentMetadata(
  documentId: string,
  updates: { filename?: string; document_type?: string; summary?: string },
): Promise<SavedMedicalDocument> {
  const url = `${getApiBaseUrl()}/api/documents/${encodeURIComponent(documentId)}`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  return handleResponse<SavedMedicalDocument>(
    res,
    "Failed to update document metadata",
  );
}

/** Delete a saved document and its linked diagnoses, medications, and lab results. */
export async function deleteSavedDocument(documentId: string): Promise<void> {
  const url = `${getApiBaseUrl()}/api/documents/${encodeURIComponent(documentId)}`;
  const res = await fetch(url, { method: "DELETE" });
  await handleResponse<{ status: string; id: string }>(
    res,
    "Failed to delete document from database",
  );
}

/** Generate patient-friendly Telugu health explanation using Gemini AI. */
export async function explainExtractionInTelugu(
  extraction: MedicalDocumentExtraction,
): Promise<TeluguHealthSummary> {
  const url = `${getApiBaseUrl()}/api/documents/explain-telugu`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ extraction }),
  });
  return handleResponse<TeluguHealthSummary>(
    res,
    "Failed to generate Telugu clinical explanation",
  );
}

/** Fetch Telugu health explanation for a persisted document. */
export async function fetchDocumentTeluguExplanation(
  documentId: string,
): Promise<TeluguHealthSummary> {
  const url = `${getApiBaseUrl()}/api/documents/${encodeURIComponent(documentId)}/explain-telugu`;
  const res = await fetch(url, { method: "GET" });
  return handleResponse<TeluguHealthSummary>(
    res,
    `Failed to generate Telugu explanation for document '${documentId}'`,
  );
}

/** Export a persisted patient's complete records as an HL7 FHIR R4 Bundle. */
export async function exportPatientFhirBundle(
  patientId: string,
): Promise<FhirBundle> {
  const url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/fhir`;
  const res = await fetch(url, { method: "GET" });
  return handleResponse<FhirBundle>(
    res,
    `Failed to export FHIR bundle for patient '${patientId}'`,
  );
}

/** Export a single persisted document's records as an HL7 FHIR R4 Bundle. */
export async function exportDocumentFhirBundle(
  documentId: string,
): Promise<FhirBundle> {
  const url = `${getApiBaseUrl()}/api/documents/${encodeURIComponent(documentId)}/fhir`;
  const res = await fetch(url, { method: "GET" });
  return handleResponse<FhirBundle>(
    res,
    `Failed to export FHIR bundle for document '${documentId}'`,
  );
}

