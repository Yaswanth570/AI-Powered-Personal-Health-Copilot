import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Check,
  CheckCircle2,
  Database,
  Edit3,
  FileText,
  ImageIcon,
  Loader2,
  RefreshCw,
  RotateCcw,
  Save,
  Share2,
  Sparkles,
  Trash2,
} from "lucide-react";
import type {
  AiAnalysisState,
  ExtractionStatus,
  MedicalDocumentExtraction,
  MedicalRecord,
  OcrExtractionResult,
  PatientRecord,
  PdfExtractionResult,
  SavedMedicalDocument,
} from "../../types";
import {
  AiAnalysisApiError,
  analyzeDocumentWithAi,
  extractPdfText,
  extractTextWithOcr,
  PdfExtractionApiError,
} from "../../lib/pdfApi";
import {
  deleteSavedDocument,
  fetchDocumentDetail,
  saveDocumentToDatabase,
  updateDocumentMetadata,
} from "../../lib/persistenceApi";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Dialog } from "../ui/dialog";
import { AiAnalysisView } from "./AiAnalysisView";
import { FhirExportDialog } from "./FhirExportDialog";
import { SavedRelationalView } from "./SavedRelationalView";

interface RecentRecordsProps {
  records: MedicalRecord[];
  searchQuery: string;
  currentPatient?: PatientRecord | null;
  onRecordSaved?: (recordId: string, savedDoc: SavedMedicalDocument) => void;
  onRecordDeleted?: (recordId: string, docId: string) => void;
  onRecordUpdated?: (recordId: string, updatedDoc: SavedMedicalDocument) => void;
  onRefreshRecords?: () => void;
}

type ExtractionResult = PdfExtractionResult | OcrExtractionResult;

interface ExtractionState {
  status: ExtractionStatus;
  result?: ExtractionResult;
  errorMessage?: string;
}

interface SaveRecordState {
  status: "idle" | "confirming" | "saving" | "success" | "error";
  errorMessage?: string;
}

function getExtension(name: string): string {
  const sep = name.lastIndexOf(".");
  return sep >= 0 ? name.slice(sep).toLowerCase() : "";
}

function isPdf(record: MedicalRecord): boolean {
  return getExtension(record.name) === ".pdf";
}

function isImage(record: MedicalRecord): boolean {
  const ext = getExtension(record.name);
  return ext === ".jpg" || ext === ".jpeg" || ext === ".png";
}

/** Session PDFs are eligible for selectable-text extraction. */
function canExtractText(record: MedicalRecord): boolean {
  return record.origin === "session" && isPdf(record) && Boolean(record.file);
}

/** Session PDFs and images are eligible for OCR. */
function canExtractWithOcr(record: MedicalRecord): boolean {
  return (
    record.origin === "session" &&
    (isPdf(record) || isImage(record)) &&
    Boolean(record.file)
  );
}

function isOcrResult(result: ExtractionResult): result is OcrExtractionResult {
  return "ocr_engine" in result;
}

function resultHasText(result: ExtractionResult): boolean {
  return isOcrResult(result) ? result.has_text : result.has_selectable_text;
}

function toExtractionView(doc: SavedMedicalDocument): MedicalDocumentExtraction {
  if (doc.ai_extraction_json) {
    return doc.ai_extraction_json;
  }
  return {
    document_type: String(doc.document_type || "Other"),
    report_date: doc.upload_date,
    patient_name: null,
    patient_age: null,
    patient_gender: null,
    diagnoses:
      doc.diagnoses?.map((d) => ({
        diagnosis: d.diagnosis,
        status: d.status,
        evidence: d.evidence,
        page_number: d.page_number,
      })) || [],
    medicines:
      doc.medications?.map((m) => ({
        name: m.name,
        dose: m.dose,
        frequency: m.frequency,
        duration: m.duration,
        route: m.route,
        instructions: m.instructions,
        evidence: m.evidence,
        page_number: m.page_number,
      })) || [],
    lab_tests:
      doc.lab_results?.map((l) => ({
        test_name: l.test_name,
        value: l.value,
        unit: l.unit,
        reference_range: l.reference_range,
        abnormal_flag: l.abnormal_flag,
        evidence: l.evidence,
        page_number: l.page_number,
      })) || [],
    missing_fields: [],
    uncertainties: [],
    confidence: doc.confidence || "high",
    confidence_reason: doc.confidence_reason,
    summary: doc.summary,
    disclaimer: doc.disclaimer,
    model_used: doc.model_used || "PostgreSQL Persisted",
  };
}

export function RecentRecords({
  records,
  searchQuery,
  currentPatient,
  onRecordSaved,
  onRecordDeleted,
  onRecordUpdated,
  onRefreshRecords,
}: RecentRecordsProps) {
  const [selected, setSelected] = useState<MedicalRecord | null>(null);
  const [activeTab, setActiveTab] = useState<"ai" | "raw" | "relational">("ai");
  const [extractionByRecord, setExtractionByRecord] = useState<
    Record<string, ExtractionState>
  >({});
  const [aiAnalysisByRecord, setAiAnalysisByRecord] = useState<
    Record<string, AiAnalysisState>
  >({});
  const [saveStatusByRecord, setSaveStatusByRecord] = useState<
    Record<string, SaveRecordState>
  >({});

  // Detail cache for persisted records
  const [cachedDetails, setCachedDetails] = useState<
    Record<string, SavedMedicalDocument>
  >({});
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Edit metadata modal state
  const [isEditing, setIsEditing] = useState(false);
  const [editFilename, setEditFilename] = useState("");
  const [editDocType, setEditDocType] = useState("");
  const [isUpdatingMetadata, setIsUpdatingMetadata] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // Delete confirmation state
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // FHIR Export dialog state
  const [fhirExportConfig, setFhirExportConfig] = useState<{
    open: boolean;
    mode: "document" | "patient";
    targetId: string;
    titleName: string;
  }>({
    open: false,
    mode: "document",
    targetId: "",
    titleName: "",
  });

  // Load detail whenever a database record is selected
  useEffect(() => {
    if (!selected || selected.origin !== "database") {
      return;
    }
    const docId = selected.persistedId || selected.id.replace(/^db-/, "");
    if (cachedDetails[docId]?.diagnoses) {
      return;
    }

    let isMounted = true;
    setIsLoadingDetail(true);
    fetchDocumentDetail(docId)
      .then((detail) => {
        if (isMounted) {
          setCachedDetails((prev) => ({ ...prev, [docId]: detail }));
        }
      })
      .catch((err) => {
        console.error("Failed to load document detail:", err);
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingDetail(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selected, cachedDetails]);

  function extractionOf(recordId: string): ExtractionState {
    return extractionByRecord[recordId] ?? { status: "idle" };
  }

  function aiAnalysisOf(recordId: string): AiAnalysisState {
    return aiAnalysisByRecord[recordId] ?? { status: "idle" };
  }

  function saveStatusOf(recordId: string): SaveRecordState {
    return saveStatusByRecord[recordId] ?? { status: "idle" };
  }

  async function handleExtract(record: MedicalRecord, useOcr: boolean) {
    if (!record.file) {
      return;
    }
    setExtractionByRecord((current) => ({
      ...current,
      [record.id]: { status: "loading" },
    }));

    try {
      const result = useOcr
        ? await extractTextWithOcr(record.file)
        : await extractPdfText(record.file);
      setExtractionByRecord((current) => ({
        ...current,
        [record.id]: { status: "success", result },
      }));
      setSelected(record);
      setActiveTab("raw");
    } catch (error) {
      const message =
        error instanceof PdfExtractionApiError
          ? error.message
          : "Text extraction could not be completed. Please try again.";
      setExtractionByRecord((current) => ({
        ...current,
        [record.id]: { status: "error", errorMessage: message },
      }));
      setSelected(record);
      setActiveTab("raw");
    }
  }

  async function handleAnalyzeWithAi(record: MedicalRecord) {
    if (!record.file) {
      return;
    }

    let currentExtraction = extractionOf(record.id);
    if (
      currentExtraction.status !== "success" ||
      !currentExtraction.result ||
      !resultHasText(currentExtraction.result)
    ) {
      setExtractionByRecord((prev) => ({
        ...prev,
        [record.id]: { status: "loading" },
      }));
      setAiAnalysisByRecord((prev) => ({
        ...prev,
        [record.id]: { status: "loading" },
      }));

      try {
        const isPdfDoc = isPdf(record);
        let extractedResult: ExtractionResult;
        if (isPdfDoc) {
          extractedResult = await extractPdfText(record.file);
          if (!extractedResult.has_selectable_text) {
            extractedResult = await extractTextWithOcr(record.file);
          }
        } else {
          extractedResult = await extractTextWithOcr(record.file);
        }

        currentExtraction = { status: "success", result: extractedResult };
        setExtractionByRecord((prev) => ({
          ...prev,
          [record.id]: currentExtraction,
        }));
      } catch (err) {
        const msg =
          err instanceof PdfExtractionApiError
            ? err.message
            : "Text extraction failed before AI analysis could begin.";
        setExtractionByRecord((prev) => ({
          ...prev,
          [record.id]: { status: "error", errorMessage: msg },
        }));
        setAiAnalysisByRecord((prev) => ({
          ...prev,
          [record.id]: { status: "error", errorMessage: msg },
        }));
        return;
      }
    }

    if (!currentExtraction.result || !resultHasText(currentExtraction.result)) {
      setAiAnalysisByRecord((prev) => ({
        ...prev,
        [record.id]: {
          status: "error",
          errorMessage:
            "No readable text was detected in this document. AI clinical extraction requires text content.",
        },
      }));
      return;
    }

    setAiAnalysisByRecord((prev) => ({
      ...prev,
      [record.id]: { status: "loading" },
    }));

    try {
      const aiResult = await analyzeDocumentWithAi(
        currentExtraction.result.full_text,
        currentExtraction.result.pages,
        record.type,
      );
      setAiAnalysisByRecord((prev) => ({
        ...prev,
        [record.id]: { status: "success", result: aiResult },
      }));
      setSelected(record);
      setActiveTab("ai");
    } catch (err) {
      const msg =
        err instanceof AiAnalysisApiError
          ? err.message
          : "Gemini AI extraction could not be completed. Please check your network and GEMINI_API_KEY.";
      setAiAnalysisByRecord((prev) => ({
        ...prev,
        [record.id]: { status: "error", errorMessage: msg },
      }));
      setSelected(record);
      setActiveTab("ai");
    }
  }

  async function handleSaveDocumentToDatabase(record: MedicalRecord) {
    const aiState = aiAnalysisOf(record.id);
    const extState = extractionOf(record.id);

    if (aiState.status !== "success" || !aiState.result) {
      return;
    }

    setSaveStatusByRecord((prev) => ({
      ...prev,
      [record.id]: { status: "saving" },
    }));

    try {
      // Use current patient ID or fallback to standard seeded demo patient
      const patientId = currentPatient?.id || "demo-patient-sunita-rao";
      const aiResult = aiState.result;

      const savedDoc = await saveDocumentToDatabase({
        patient_id: patientId,
        filename: record.name,
        document_type: aiResult.document_type || record.type,
        upload_date: aiResult.report_date || new Date().toISOString().slice(0, 10),
        processing_status: "analyzed",
        ai_analysis_status: "success",
        page_count: extState.result?.page_count || 1,
        total_char_count: extState.result?.total_char_count || 0,
        extraction_method:
          extState.result && isOcrResult(extState.result) ? "ocr" : "selectable",
        confidence: aiResult.confidence,
        confidence_reason: aiResult.confidence_reason,
        summary: aiResult.summary,
        disclaimer: aiResult.disclaimer,
        model_used: aiResult.model_used,
        raw_text: extState.result?.full_text || null,
        ai_extraction: aiResult,
      });

      setSaveStatusByRecord((prev) => ({
        ...prev,
        [record.id]: { status: "success" },
      }));

      // Cache details
      setCachedDetails((prev) => ({ ...prev, [savedDoc.id]: savedDoc }));

      // Notify parent to transition record to database origin
      if (onRecordSaved) {
        onRecordSaved(record.id, savedDoc);
      }

      // Update active selection to point to persisted document
      setSelected({
        ...record,
        origin: "database",
        status: "Saved in Database",
        persistedDoc: savedDoc,
        persistedId: savedDoc.id,
      });
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Failed to persist document to database.";
      setSaveStatusByRecord((prev) => ({
        ...prev,
        [record.id]: { status: "error", errorMessage: msg },
      }));
    }
  }

  async function handleConfirmDelete() {
    if (!selected) return;
    const docId = selected.persistedId || selected.id.replace(/^db-/, "");
    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteSavedDocument(docId);
      if (onRecordDeleted) {
        onRecordDeleted(selected.id, docId);
      }
      setIsConfirmingDelete(false);
      setSelected(null);
    } catch (err) {
      setDeleteError(
        err instanceof Error ? err.message : "Failed to delete document from database.",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleSaveMetadata() {
    if (!selected) return;
    const docId = selected.persistedId || selected.id.replace(/^db-/, "");
    setIsUpdatingMetadata(true);
    setEditError(null);

    try {
      const updated = await updateDocumentMetadata(docId, {
        filename: editFilename.trim() || undefined,
        document_type: editDocType.trim() || undefined,
      });
      setCachedDetails((prev) => ({ ...prev, [docId]: updated }));
      if (onRecordUpdated) {
        onRecordUpdated(selected.id, updated);
      }
      setSelected((prev) =>
        prev
          ? {
              ...prev,
              name: updated.filename,
              type: (updated.document_type as any) || prev.type,
              persistedDoc: updated,
            }
          : null,
      );
      setIsEditing(false);
    } catch (err) {
      setEditError(
        err instanceof Error ? err.message : "Failed to update document metadata.",
      );
    } finally {
      setIsUpdatingMetadata(false);
    }
  }

  function clearExtraction(recordId: string) {
    setExtractionByRecord((current) => {
      const next = { ...current };
      delete next[recordId];
      return next;
    });
    setAiAnalysisByRecord((current) => {
      const next = { ...current };
      delete next[recordId];
      return next;
    });
    setSaveStatusByRecord((current) => {
      const next = { ...current };
      delete next[recordId];
      return next;
    });
  }

  const activeExtraction = selected ? extractionOf(selected.id) : { status: "idle" as const };
  const activeAi = selected ? aiAnalysisOf(selected.id) : { status: "idle" as const };
  const activeSave = selected ? saveStatusOf(selected.id) : { status: "idle" as const };

  // Current selected database document details
  const selectedDbDoc = useMemo(() => {
    if (!selected || selected.origin !== "database") {
      return null;
    }
    const docId = selected.persistedId || selected.id.replace(/^db-/, "");
    return cachedDetails[docId] || selected.persistedDoc || null;
  }, [selected, cachedDetails]);

  const recordCountText = useMemo(() => {
    const sessionCount = records.filter((r) => r.origin === "session").length;
    const dbCount = records.filter((r) => r.origin === "database").length;
    if (dbCount > 0 && sessionCount > 0) {
      return `${dbCount} persisted in database, ${sessionCount} in active session (not saved).`;
    }
    if (dbCount > 0) {
      return `${dbCount} document${dbCount === 1 ? "" : "s"} persisted in PostgreSQL database.`;
    }
    if (sessionCount > 0) {
      return `${sessionCount} session document${sessionCount === 1 ? "" : "s"} listed in this tab (not saved).`;
    }
    return "";
  }, [records]);

  const dialogTitle =
    selected?.origin === "database"
      ? `Persisted Health Record: ${selected.name}`
      : selected?.origin === "session"
        ? activeAi.status === "success" && activeTab === "ai"
          ? "Gemini AI Clinical Extraction"
          : activeExtraction.status === "success" && activeExtraction.result
            ? resultHasText(activeExtraction.result)
              ? isOcrResult(activeExtraction.result)
                ? "OCR-recognized text"
                : "Extracted PDF text"
              : "Session document"
            : "Session document"
        : "Sample document metadata";

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>Medical Records & Persistence</CardTitle>
            <CardDescription>
              PostgreSQL persistent health repository with transactional storage of diagnoses,
              medications, and lab investigations.
              {recordCountText ? ` ${recordCountText}` : ""}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {currentPatient ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFhirExportConfig({
                    open: true,
                    mode: "patient",
                    targetId: currentPatient.id,
                    titleName: currentPatient.display_name,
                  });
                }}
                className="gap-1.5 text-xs border-primary/40 text-primary hover:bg-primary/10"
              >
                <Share2 className="h-3.5 w-3.5" aria-hidden="true" />
                Export Patient FHIR Bundle
              </Button>
            ) : null}
            {onRefreshRecords ? (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefreshRecords}
                className="gap-1.5 text-xs"
              >
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
                Refresh from Database
              </Button>
            ) : null}
          </div>
        </div>

        {currentPatient ? (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground border-t border-border pt-2.5">
            <span className="font-medium text-foreground">Active Patient:</span>
            <span className="font-semibold text-primary">{currentPatient.display_name}</span>
            {currentPatient.age ? <span>· {currentPatient.age} yrs</span> : null}
            {currentPatient.gender ? <span>· {currentPatient.gender}</span> : null}
            <Badge tone="calm" className="text-[10px] ml-1">
              Local PostgreSQL Storage
            </Badge>
          </div>
        ) : null}
      </CardHeader>

      {records.length === 0 ? (
        <p className="rounded-md border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
          No records match “{searchQuery}”.
        </p>
      ) : (
        <>
          <div className="hidden overflow-x-auto md:block">
            <table className="w-full min-w-[46rem] text-left text-sm">
              <caption className="sr-only">Medical records list</caption>
              <thead className="border-b border-border text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Document name
                  </th>
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Type
                  </th>
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Date
                  </th>
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Persistence & Status
                  </th>
                  <th scope="col" className="py-3 font-medium">
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => {
                  const extraction = extractionOf(record.id);
                  const aiAnalysis = aiAnalysisOf(record.id);
                  const isAnalyzing = aiAnalysis.status === "loading";
                  const isExtracting = extraction.status === "loading";
                  const hasAiResult = aiAnalysis.status === "success";
                  const isDb = record.origin === "database";
                  const isSession = record.origin === "session";

                  return (
                    <tr key={record.id} className="border-b border-border last:border-0">
                      <td className="py-3 pr-4">
                        <div className="flex items-center gap-2">
                          {isDb ? (
                            <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                          ) : (
                            <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                          )}
                          <div>
                            <p className="font-medium text-foreground">{record.name}</p>
                            {record.fileSizeLabel ? (
                              <p className="text-xs text-muted-foreground">
                                {record.fileSizeLabel}
                              </p>
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-muted-foreground">{record.type}</td>
                      <td className="py-3 pr-4 text-muted-foreground">{record.uploadedOn}</td>
                      <td className="py-3 pr-4">
                        <div className="flex flex-wrap items-center gap-1.5">
                          {isDb ? (
                            <Badge tone="calm" className="gap-1 border-emerald-500/30 text-emerald-700 dark:text-emerald-300">
                              <CheckCircle2 className="h-3 w-3" />
                              Saved in DB
                            </Badge>
                          ) : isSession ? (
                            <Badge tone="warn" className="gap-1">
                              Session (Unsaved)
                            </Badge>
                          ) : (
                            <Badge tone="neutral">Demo</Badge>
                          )}
                          {hasAiResult && !isDb ? (
                            <Badge tone="calm" className="gap-1">
                              <Sparkles className="h-3 w-3" aria-hidden="true" />
                              AI Analyzed
                            </Badge>
                          ) : null}
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setSelected(record);
                              setActiveTab(isDb ? "relational" : hasAiResult ? "ai" : "raw");
                            }}
                          >
                            View
                          </Button>

                          {isDb ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                const docId = record.persistedId || record.id.replace(/^db-/, "");
                                setFhirExportConfig({
                                  open: true,
                                  mode: "document",
                                  targetId: docId,
                                  titleName: record.name,
                                });
                              }}
                              className="border-primary/40 text-primary hover:bg-primary/10 gap-1 text-xs"
                            >
                              <Share2 className="h-3.5 w-3.5" />
                              FHIR Export
                            </Button>
                          ) : null}

                          {/* Action for session files: Analyze with AI */}
                          {isSession && record.file ? (
                            <Button
                              size="sm"
                              variant={hasAiResult ? "outline" : "default"}
                              onClick={() => handleAnalyzeWithAi(record)}
                              disabled={isAnalyzing || isExtracting}
                              className={
                                !hasAiResult
                                  ? "bg-primary text-primary-foreground shadow-xs hover:bg-primary/90"
                                  : ""
                              }
                            >
                              {isAnalyzing ? (
                                <>
                                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                                  Analyzing…
                                </>
                              ) : (
                                <>
                                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                                  {hasAiResult ? "Re-analyze" : "Analyze with AI"}
                                </>
                              )}
                            </Button>
                          ) : null}

                          {canExtractText(record) ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleExtract(record, false)}
                              disabled={isExtracting || isAnalyzing}
                            >
                              {isExtracting ? (
                                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                              ) : (
                                <FileText className="h-4 w-4" aria-hidden="true" />
                              )}
                              PDF Text
                            </Button>
                          ) : null}

                          {canExtractWithOcr(record) ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleExtract(record, true)}
                              disabled={isExtracting || isAnalyzing}
                            >
                              {isExtracting ? (
                                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                              ) : (
                                <ImageIcon className="h-4 w-4" aria-hidden="true" />
                              )}
                              OCR
                            </Button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <ul className="space-y-3 md:hidden">
            {records.map((record) => {
              const extraction = extractionOf(record.id);
              const aiAnalysis = aiAnalysisOf(record.id);
              const isAnalyzing = aiAnalysis.status === "loading";
              const isExtracting = extraction.status === "loading";
              const hasAiResult = aiAnalysis.status === "success";
              const isDb = record.origin === "database";
              const isSession = record.origin === "session";

              return (
                <li key={record.id} className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2">
                    {isDb ? (
                      <Database className="h-4 w-4 text-emerald-600 shrink-0" />
                    ) : (
                      <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                    )}
                    <p className="font-medium text-foreground">{record.name}</p>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {record.type} · {record.uploadedOn}
                    {record.fileSizeLabel ? ` · ${record.fileSizeLabel}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    {isDb ? (
                      <Badge tone="calm" className="gap-1">
                        <CheckCircle2 className="h-3 w-3" />
                        Saved in DB
                      </Badge>
                    ) : isSession ? (
                      <Badge tone="warn">Session (Unsaved)</Badge>
                    ) : (
                      <Badge tone="neutral">Demo</Badge>
                    )}
                    {hasAiResult && !isDb ? (
                      <Badge tone="calm" className="gap-1">
                        <Sparkles className="h-3 w-3" aria-hidden="true" />
                        AI Analyzed
                      </Badge>
                    ) : null}
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setSelected(record);
                        setActiveTab(isDb ? "relational" : hasAiResult ? "ai" : "raw");
                      }}
                    >
                      View
                    </Button>
                    {isSession && record.file ? (
                      <Button
                        size="sm"
                        variant={hasAiResult ? "outline" : "default"}
                        onClick={() => handleAnalyzeWithAi(record)}
                        disabled={isAnalyzing || isExtracting}
                      >
                        {isAnalyzing ? (
                          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        ) : (
                          <Sparkles className="h-4 w-4" aria-hidden="true" />
                        )}
                        {hasAiResult ? "Re-analyze" : "Analyze with AI"}
                      </Button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {/* Main Document Review Dialog */}
      <Dialog
        open={selected !== null}
        title={dialogTitle}
        description={
          selected?.origin === "database"
            ? "Persisted in PostgreSQL database with normalized diagnoses, medications, and lab findings. Changes survive browser reload."
            : selected?.origin === "session"
              ? activeAi.status === "success" && activeTab === "ai"
                ? "Structured clinical entities extracted using Gemini AI. Verify all items before saving to database."
                : activeExtraction.status === "success" && activeExtraction.result
                  ? resultHasText(activeExtraction.result)
                    ? isOcrResult(activeExtraction.result)
                      ? "Raw text recognized with OCR."
                      : "Raw text extracted from selectable PDF content."
                    : "No text was detected in this document."
                  : activeExtraction.status === "error"
                    ? "Text extraction failed."
                    : "Session document stored in browser memory only (not yet saved to PostgreSQL)."
              : "This is a labelled demo record for layout review."
        }
        onClose={() => {
          setSelected(null);
          setIsConfirmingDelete(false);
          setIsEditing(false);
        }}
      >
        {selected ? (
          <div className="space-y-5">
            {/* Metadata Summary Banner */}
            <dl className="grid grid-cols-2 gap-3 rounded-lg border border-border bg-muted/20 p-3 text-xs sm:grid-cols-4">
              <div>
                <dt className="text-muted-foreground">Document name</dt>
                <dd
                  className="mt-0.5 font-medium truncate text-foreground"
                  title={selected.name}
                >
                  {selected.name}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Document type</dt>
                <dd className="mt-0.5 font-medium text-foreground">{selected.type}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Storage</dt>
                <dd className="mt-0.5 text-foreground flex items-center gap-1">
                  {selected.origin === "database" ? (
                    <span className="text-emerald-600 font-semibold flex items-center gap-1">
                      <Database className="h-3 w-3" /> PostgreSQL
                    </span>
                  ) : selected.origin === "session" ? (
                    <span className="text-amber-600 font-medium">Session Memory (Unsaved)</span>
                  ) : (
                    <span className="text-muted-foreground">Demo</span>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Date</dt>
                <dd className="mt-0.5 text-foreground">{selected.uploadedOn}</dd>
              </div>
            </dl>

            {/* If Persisted Record: Top Action Bar (Edit Metadata & Delete) */}
            {selected.origin === "database" ? (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-950 dark:text-emerald-100">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span>
                    Database ID: <code className="font-mono">{selected.persistedId || selected.id.replace(/^db-/, "")}</code>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs gap-1 border-primary/40 text-primary hover:bg-primary/10"
                    onClick={() => {
                      const docId = selected.persistedId || selected.id.replace(/^db-/, "");
                      setFhirExportConfig({
                        open: true,
                        mode: "document",
                        targetId: docId,
                        titleName: selected.name,
                      });
                    }}
                  >
                    <Share2 className="h-3.5 w-3.5" />
                    FHIR R4 Export
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs gap-1"
                    onClick={() => {
                      setEditFilename(selected.name);
                      setEditDocType(selected.type);
                      setIsEditing(true);
                    }}
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    Edit Metadata
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7 text-xs gap-1 border-red-500/50 text-red-600 hover:bg-red-500/10 dark:text-red-400"
                    onClick={() => setIsConfirmingDelete(true)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete Record
                  </Button>
                </div>
              </div>
            ) : null}

            {/* Inline Edit Metadata Form */}
            {isEditing && selected.origin === "database" ? (
              <div className="rounded-lg border border-primary/40 bg-card p-4 space-y-3">
                <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Edit3 className="h-3.5 w-3.5 text-primary" />
                  Update Document Metadata (PostgreSQL PATCH)
                </h4>
                {editError ? (
                  <p className="text-xs text-red-600">{editError}</p>
                ) : null}
                <div className="grid gap-3 sm:grid-cols-2 text-xs">
                  <div>
                    <label className="text-muted-foreground font-medium">Filename</label>
                    <input
                      type="text"
                      value={editFilename}
                      onChange={(e) => setEditFilename(e.target.value)}
                      className="mt-1 w-full rounded border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label className="text-muted-foreground font-medium">Document Type</label>
                    <input
                      type="text"
                      value={editDocType}
                      onChange={(e) => setEditDocType(e.target.value)}
                      className="mt-1 w-full rounded border border-border bg-background px-2.5 py-1.5 text-xs text-foreground focus:outline-hidden focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsEditing(false)}
                    disabled={isUpdatingMetadata}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSaveMetadata}
                    disabled={isUpdatingMetadata || !editFilename.trim()}
                  >
                    {isUpdatingMetadata ? (
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                    ) : (
                      <Check className="h-3 w-3 mr-1" />
                    )}
                    Save Changes
                  </Button>
                </div>
              </div>
            ) : null}

            {/* Inline Delete Confirmation Alert */}
            {isConfirmingDelete && selected.origin === "database" ? (
              <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 space-y-3 text-red-950 dark:text-red-100">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-semibold">
                      Confirm Safe Cascade Deletion
                    </h4>
                    <p className="text-xs mt-1 leading-relaxed">
                      Are you sure you want to permanently delete <strong>{selected.name}</strong> from the database?
                      All linked diagnosis, medication, and lab result rows will be safely removed in an atomic transaction.
                    </p>
                    {deleteError ? (
                      <p className="text-xs text-red-600 font-medium mt-1">{deleteError}</p>
                    ) : null}
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => setIsConfirmingDelete(false)}
                    disabled={isDeleting}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    variant="default"
                    onClick={handleConfirmDelete}
                    disabled={isDeleting}
                    className="bg-red-600 hover:bg-red-700 text-white"
                  >
                    {isDeleting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />
                    ) : (
                      <Trash2 className="h-3.5 w-3.5 mr-1" />
                    )}
                    Confirm Delete
                  </Button>
                </div>
              </div>
            ) : null}

            {/* View Tabs Header */}
            <div className="flex items-center rounded-lg border border-border bg-muted/40 p-1 text-xs">
              {selected.origin === "database" ? (
                <button
                  type="button"
                  onClick={() => setActiveTab("relational")}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
                    activeTab === "relational"
                      ? "bg-background text-foreground shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <Database className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                  Structured SQL Records
                </button>
              ) : null}

              <button
                type="button"
                onClick={() => setActiveTab("ai")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
                  activeTab === "ai"
                    ? "bg-background text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                AI Analysis View
                {activeAi.status === "success" && selected.origin === "session" ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                ) : null}
              </button>

              <button
                type="button"
                onClick={() => setActiveTab("raw")}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-all ${
                  activeTab === "raw"
                    ? "bg-background text-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                Original Text
              </button>
            </div>

            {/* TAB CONTENT: Database Relational Records */}
            {activeTab === "relational" && selected.origin === "database" ? (
              <div className="space-y-4">
                {isLoadingDetail ? (
                  <div className="flex items-center justify-center py-8 text-xs text-muted-foreground gap-2">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    Loading relational records from PostgreSQL…
                  </div>
                ) : selectedDbDoc ? (
                  <SavedRelationalView document={selectedDbDoc} />
                ) : (
                  <p className="text-xs text-muted-foreground py-4">No records loaded.</p>
                )}
              </div>
            ) : null}

            {/* TAB CONTENT: AI Analysis */}
            {activeTab === "ai" ? (
              <div className="space-y-4">
                {selected.origin === "database" ? (
                  isLoadingDetail ? (
                    <div className="flex items-center justify-center py-8 text-xs text-muted-foreground gap-2">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      Loading AI extraction from database…
                    </div>
                  ) : selectedDbDoc ? (
                    <AiAnalysisView extraction={toExtractionView(selectedDbDoc)} />
                  ) : null
                ) : selected.origin === "session" ? (
                  <>
                    {/* Session AI Loading */}
                    {activeAi.status === "loading" ? (
                      <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-muted/20 py-12 text-center space-y-3">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-foreground">
                            Analyzing document with Gemini AI…
                          </p>
                          <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                            Extracting diagnoses, medicines with exact doses, and lab test values with
                            strict clinical fidelity and zero hallucination.
                          </p>
                        </div>
                      </div>
                    ) : null}

                    {/* Session AI Error */}
                    {activeAi.status === "error" ? (
                      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-900 dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-200 space-y-3">
                        <div className="flex items-start gap-3">
                          <AlertCircle
                            className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400"
                            aria-hidden="true"
                          />
                          <div className="space-y-1">
                            <p className="font-semibold text-amber-950 dark:text-amber-100">
                              AI Extraction Could Not Be Completed
                            </p>
                            <p className="text-xs sm:text-sm leading-relaxed">
                              {activeAi.errorMessage}
                            </p>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => handleAnalyzeWithAi(selected)}
                        >
                          <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                          Retry AI Analysis
                        </Button>
                      </div>
                    ) : null}

                    {/* Session AI Success: Display Extraction + Explicit PostgreSQL Save Action */}
                    {activeAi.status === "success" && activeAi.result ? (
                      <div className="space-y-6">
                        {/* Save to PostgreSQL Callout */}
                        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-3 shadow-xs">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex items-start gap-2.5">
                              <Database className="h-5 w-5 text-primary mt-0.5 shrink-0" />
                              <div>
                                <h4 className="text-sm font-semibold text-foreground">
                                  Save to Health Records (PostgreSQL Database)
                                </h4>
                                <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                                  Save this document and its validated findings (
                                  {activeAi.result.diagnoses.length} diagnoses,{" "}
                                  {activeAi.result.medicines.length} medicines,{" "}
                                  {activeAi.result.lab_tests.length} lab investigations)
                                  to your database in an atomic transaction.
                                </p>
                              </div>
                            </div>
                          </div>

                          {/* Save Status / Confirmation */}
                          {activeSave.status === "confirming" ? (
                            <div className="rounded border border-primary/40 bg-background p-3 text-xs space-y-2">
                              <p className="font-medium text-foreground">
                                Confirm saving document “{selected.name}” for patient{" "}
                                <strong>{currentPatient?.display_name || "Smt. Sunita Rao"}</strong>?
                              </p>
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={() => handleSaveDocumentToDatabase(selected)}
                                  className="bg-primary text-primary-foreground gap-1"
                                >
                                  <Check className="h-3.5 w-3.5" />
                                  Confirm & Save to Database
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() =>
                                    setSaveStatusByRecord((prev) => ({
                                      ...prev,
                                      [selected.id]: { status: "idle" },
                                    }))
                                  }
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : activeSave.status === "saving" ? (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
                              <Loader2 className="h-4 w-4 animate-spin text-primary" />
                              Committing document and clinical findings in database transaction…
                            </div>
                          ) : activeSave.status === "error" ? (
                            <div className="rounded border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-950 dark:text-red-200 space-y-2">
                              <p className="font-semibold">Save failed: {activeSave.errorMessage}</p>
                              <p className="text-[11px] text-muted-foreground">
                                Your extracted clinical data has NOT been lost. You can retry anytime.
                              </p>
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => handleSaveDocumentToDatabase(selected)}
                                className="gap-1"
                              >
                                <RotateCcw className="h-3 w-3" />
                                Retry Save to Database
                              </Button>
                            </div>
                          ) : activeSave.status === "success" ? (
                            <div className="flex items-center gap-2 rounded border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-950 dark:text-emerald-200">
                              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0" />
                              <span>
                                Document and clinical extractions were successfully committed to PostgreSQL!
                              </span>
                            </div>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() =>
                                setSaveStatusByRecord((prev) => ({
                                  ...prev,
                                  [selected.id]: { status: "confirming" },
                                }))
                              }
                              className="bg-primary text-primary-foreground gap-1.5 shadow-xs"
                            >
                              <Save className="h-4 w-4" />
                              Save to Health Records (PostgreSQL)
                            </Button>
                          )}
                        </div>

                        {/* Extracted Content View */}
                        <AiAnalysisView extraction={activeAi.result} />
                      </div>
                    ) : null}

                    {/* Session AI Idle */}
                    {activeAi.status === "idle" ? (
                      <div className="rounded-lg border border-dashed border-border py-8 px-4 text-center space-y-3">
                        <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
                          <Sparkles className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <div className="space-y-1">
                          <p className="text-sm font-medium text-foreground">
                            Clinical AI Extraction Not Yet Run
                          </p>
                          <p className="text-xs text-muted-foreground max-w-md mx-auto">
                            Click “Analyze with AI” to use Gemini to extract diagnoses, medications,
                            and laboratory test values with structured validation.
                          </p>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => handleAnalyzeWithAi(selected)}
                          className="bg-primary text-primary-foreground"
                        >
                          <Sparkles className="h-4 w-4 mr-1.5" />
                          Analyze with AI Now
                        </Button>
                      </div>
                    ) : null}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">Demo record view.</p>
                )}
              </div>
            ) : null}

            {/* TAB CONTENT: Raw Extracted Text */}
            {activeTab === "raw" ? (
              <div className="space-y-4">
                {selected.origin === "database" ? (
                  selectedDbDoc?.raw_text ? (
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">
                        Raw verifiable text stored in database:
                      </p>
                      <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-md border border-border bg-card p-3 font-sans text-xs leading-6 text-foreground">
                        {selectedDbDoc.raw_text}
                      </pre>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground italic">
                      No raw text was stored for this document.
                    </p>
                  )
                ) : selected.origin === "session" ? (
                  activeExtraction.status === "idle" ? (
                    <p className="text-sm text-muted-foreground">
                      No text has been extracted yet. Choose “PDF Text” or “OCR” above to extract
                      selectable text or image text.
                    </p>
                  ) : activeExtraction.status === "loading" ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground py-6 justify-center">
                      <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
                      Extracting raw text from document…
                    </div>
                  ) : activeExtraction.status === "error" ? (
                    <div className="flex items-start gap-2 rounded-md border border-warning-border bg-warning-bg px-3 py-2 text-sm text-warning">
                      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                      <p>{activeExtraction.errorMessage}</p>
                    </div>
                  ) : activeExtraction.status === "success" && activeExtraction.result ? (
                    <ExtractionReview result={activeExtraction.result} />
                  ) : null
                ) : null}
              </div>
            ) : null}

            {/* Clear session extraction footer */}
            {(activeExtraction.status !== "idle" || activeAi.status !== "idle") &&
            selected.origin === "session" ? (
              <div className="flex justify-end pt-2 border-t border-border">
                <Button variant="ghost" size="sm" onClick={() => clearExtraction(selected.id)}>
                  Clear extraction and AI results
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      </Dialog>

      <FhirExportDialog
        open={fhirExportConfig.open}
        onClose={() => setFhirExportConfig((prev) => ({ ...prev, open: false }))}
        mode={fhirExportConfig.mode}
        targetId={fhirExportConfig.targetId}
        titleName={fhirExportConfig.titleName}
      />
    </Card>
  );
}

function ExtractionReview({ result }: { result: ExtractionResult }) {
  const ocr = isOcrResult(result);
  const hasText = resultHasText(result);
  const charCount = result.total_char_count;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm">
        {hasText ? (
          <CheckCircle2 className="h-4 w-4 text-primary" aria-hidden="true" />
        ) : (
          <AlertCircle className="h-4 w-4 text-warning" aria-hidden="true" />
        )}
        <span className="text-foreground">
          {hasText
            ? `${result.page_count} page${result.page_count === 1 ? "" : "s"}, ${charCount.toLocaleString()} characters ${ocr ? "recognized" : "extracted"}.`
            : ocr
              ? "OCR completed but no text was detected."
              : "No selectable text was found."}
        </span>
      </div>

      {ocr ? (
        <p className="text-xs leading-5 text-muted-foreground">
          OCR engine: {result.ocr_engine}
          {result.ocr_languages.length > 0
            ? ` · Languages: ${result.ocr_languages.join(", ")}`
            : ""}
        </p>
      ) : null}

      <p className="text-xs leading-5 text-muted-foreground">{result.note}</p>

      {hasText ? (
        <div className="space-y-3">
          <h4 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {ocr ? "OCR-recognized text (raw, for review)" : "Extracted text"}
          </h4>
          {result.pages.map((page) => (
            <div
              key={page.page_number}
              className="rounded-md border border-border bg-card"
            >
              <div className="border-b border-border px-3 py-2 text-xs font-medium text-muted-foreground">
                Page {page.page_number} · {page.char_count.toLocaleString()} characters
                {page.method === "ocr" ? " · OCR" : " · text layer"}
              </div>
              <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words px-3 py-3 font-sans text-sm leading-6 text-foreground">
                {page.text || "(no text on this page)"}
              </pre>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-warning-border bg-warning-bg px-3 py-3 text-sm text-warning">
          <p className="font-medium">
            {ocr ? "No text was recognized." : "This PDF has no selectable text layer."}
          </p>
          <p className="mt-1 leading-6">
            {ocr
              ? "The image may be blank, too low-resolution, or contain only handwriting that Tesseract could not recognize. No text was fabricated."
              : "It may be a scanned document or an image saved as a PDF. Use “Extract Text with OCR” to try recognizing text from the page images."}
          </p>
        </div>
      )}
    </div>
  );
}
