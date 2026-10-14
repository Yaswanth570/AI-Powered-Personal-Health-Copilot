import { medicalRecords } from "../data/demoData";
import type { MedicalRecord, SummaryCard, UploadDocumentType } from "../types";
import { formatFileSize, formatIndianDate } from "./fileValidation";

export const UPLOAD_DOCUMENT_TYPES: UploadDocumentType[] = [
  "Lab report",
  "Prescription",
  "Diagnostic report",
  "Discharge summary",
  "Other",
];

export function buildSummaryCards(records: MedicalRecord[]): SummaryCard[] {
  const sessionCount = records.filter((record) => record.origin === "session").length;
  const dbCount = records.filter((record) => record.origin === "database").length;
  const labCount = records.filter((record) => record.type === "Lab report").length;
  const prescriptionCount = records.filter((record) => record.type === "Prescription").length;

  return [
    {
      id: "records",
      label: "Medical Records",
      value: `${records.length} ${records.length === 1 ? "file" : "files"}`,
      detail:
        dbCount > 0
          ? `${dbCount} persisted in PostgreSQL database, ${sessionCount} in active session`
          : sessionCount > 0
            ? `${medicalRecords.length} demo files plus ${sessionCount} listed this session (not saved)`
            : "Synthetic demo uploads & database records",
      icon: "folder",
    },
    {
      id: "labs",
      label: "Lab Reports",
      value: `${labCount} ${labCount === 1 ? "item" : "items"}`,
      detail: "Illustrative values and session listings only",
      icon: "flask",
    },
    {
      id: "prescriptions",
      label: "Prescriptions",
      value: `${prescriptionCount} ${prescriptionCount === 1 ? "item" : "items"}`,
      detail: "Not real medications or orders",
      icon: "pill",
    },
    {
      id: "followups",
      label: "Upcoming Follow-ups",
      value: "2 sample visits",
      detail: "Placeholder calendar items",
      icon: "calendar",
    },
  ];
}

export function createSessionRecordId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `session-${crypto.randomUUID()}`;
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function isUploadDocumentType(value: string): value is UploadDocumentType {
  return UPLOAD_DOCUMENT_TYPES.some((type) => type === value);
}

export function createSessionRecord(
  file: File,
  documentType: UploadDocumentType,
): MedicalRecord {
  return {
    id: createSessionRecordId(),
    name: file.name,
    type: documentType,
    uploadedOn: formatIndianDate(),
    status: "Uploaded — analysis not yet available",
    sourceNote:
      "Listed from this browser session only. The file stays in memory, is not saved to a server, and has not been analyzed.",
    origin: "session",
    fileSizeLabel: formatFileSize(file.size),
    file,
  };
}
