import {
  AlertCircle,
  Check,
  Copy,
  Download,
  FileCode,
  FileText,
  FlaskConical,
  HeartPulse,
  Loader2,
  Pill,
  RefreshCw,
  ShieldCheck,
  Stethoscope,
  User,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  exportDocumentFhirBundle,
  exportPatientFhirBundle,
} from "../../lib/persistenceApi";
import type { FhirBundle } from "../../types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Dialog } from "../ui/dialog";

interface FhirExportDialogProps {
  open: boolean;
  onClose: () => void;
  mode: "document" | "patient";
  targetId: string;
  titleName: string;
}

export function FhirExportDialog({
  open,
  onClose,
  mode,
  targetId,
  titleName,
}: FhirExportDialogProps) {
  const [bundle, setBundle] = useState<FhirBundle | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open || !targetId) {
      setBundle(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    const fetchBundle = async () => {
      try {
        const result =
          mode === "patient"
            ? await exportPatientFhirBundle(targetId)
            : await exportDocumentFhirBundle(targetId);
        if (isMounted) {
          setBundle(result);
          setIsLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to generate FHIR R4 Bundle.",
          );
          setIsLoading(false);
        }
      }
    };

    fetchBundle();

    return () => {
      isMounted = false;
    };
  }, [open, mode, targetId]);

  const jsonString = useMemo(() => {
    if (!bundle) return "";
    return JSON.stringify(bundle, null, 2);
  }, [bundle]);

  const resourceCounts = useMemo(() => {
    if (!bundle || !bundle.entry) return {};
    const counts: Record<string, number> = {};
    for (const item of bundle.entry) {
      const type = item.resource?.resourceType || "Unknown";
      counts[type] = (counts[type] || 0) + 1;
    }
    return counts;
  }, [bundle]);

  const handleCopyJson = async () => {
    if (!jsonString) return;
    try {
      await navigator.clipboard.writeText(jsonString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard fallback
    }
  };

  const handleDownloadJson = () => {
    if (!jsonString) return;
    const sanitizedName = titleName.replace(/[^a-zA-Z0-9_-]/g, "_");
    const filename = `fhir-r4-${mode}-${sanitizedName}-${new Date().toISOString().slice(0, 10)}.json`;
    const blob = new Blob([jsonString], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={`HL7 FHIR R4 Export: ${titleName}`}
      description={
        mode === "patient"
          ? "Export all persisted records for this patient as a validated HL7 FHIR R4 Collection Bundle."
          : "Export clinical entities and document metadata as a validated HL7 FHIR R4 Collection Bundle."
      }
      className="w-[min(48rem,calc(100%-2rem))] max-h-[90vh] overflow-y-auto"
    >
      <div className="space-y-4 pt-1">
        {/* Compliance and Safety Notice */}
        <div className="rounded-lg border border-border bg-muted/40 p-3 text-xs leading-relaxed space-y-1.5">
          <div className="flex items-center gap-1.5 font-medium text-foreground">
            <ShieldCheck className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
            <span>FHIR R4 Interoperability Specification & Mapping Rules</span>
          </div>
          <p className="text-muted-foreground">
            Standard HL7 FHIR Release 4 (<code>Bundle</code> resource with <code>type: &quot;collection&quot;</code>).
            Clinical records are mapped to standard FHIR resources: <strong>Patient</strong>, <strong>DocumentReference</strong>,{" "}
            <strong>Condition</strong> (diagnoses), <strong>MedicationStatement</strong> (prescriptions), and <strong>Observation</strong> (lab tests).
            Consistent UUID references link all entities. No clinical facts are fabricated.
          </p>
        </div>

        {/* Loading State */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-background py-16 text-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm font-semibold text-foreground">
              Generating HL7 FHIR R4 Bundle…
            </p>
            <p className="text-xs text-muted-foreground max-w-sm">
              Querying database entities and mapping patient, encounter, condition, medication, and observation resources.
            </p>
          </div>
        ) : null}

        {/* Error State */}
        {error ? (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-950 dark:text-red-100 space-y-3">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-semibold">FHIR Bundle Export Failed</p>
                <p className="text-xs text-red-800 dark:text-red-200 mt-1">{error}</p>
              </div>
            </div>
            <div className="flex justify-end">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setError(null);
                  setIsLoading(true);
                  const fn =
                    mode === "patient"
                      ? exportPatientFhirBundle(targetId)
                      : exportDocumentFhirBundle(targetId);
                  fn.then(setBundle)
                    .catch((e) => setError(e.message))
                    .finally(() => setIsLoading(false));
                }}
                className="gap-1.5 text-xs"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry Export
              </Button>
            </div>
          </div>
        ) : null}

        {/* Bundle Content View */}
        {bundle && !isLoading ? (
          <div className="space-y-4">
            {/* Resource Counts Summary */}
            <div className="rounded-lg border border-border bg-card p-3 shadow-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2.5 text-xs">
                <div className="flex items-center gap-2">
                  <HeartPulse className="h-4 w-4 text-primary" />
                  <span className="font-semibold text-foreground">
                    FHIR Bundle Summary
                  </span>
                  <Badge tone="calm">
                    {bundle.total} Total Resource{bundle.total === 1 ? "" : "s"}
                  </Badge>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">
                  Timestamp: {bundle.timestamp}
                </span>
              </div>

              {/* Resource breakdown chips */}
              <div className="mt-2.5 flex flex-wrap gap-2 text-xs">
                {resourceCounts.Patient ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 px-2 py-1 text-blue-700 dark:text-blue-300">
                    <User className="h-3 w-3" />
                    Patient: {resourceCounts.Patient}
                  </span>
                ) : null}
                {resourceCounts.DocumentReference ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-purple-500/10 px-2 py-1 text-purple-700 dark:text-purple-300">
                    <FileText className="h-3 w-3" />
                    DocumentReference: {resourceCounts.DocumentReference}
                  </span>
                ) : null}
                {resourceCounts.Condition ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 px-2 py-1 text-amber-700 dark:text-amber-300">
                    <Stethoscope className="h-3 w-3" />
                    Condition: {resourceCounts.Condition}
                  </span>
                ) : null}
                {resourceCounts.MedicationStatement ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 px-2 py-1 text-emerald-700 dark:text-emerald-300">
                    <Pill className="h-3 w-3" />
                    MedicationStatement: {resourceCounts.MedicationStatement}
                  </span>
                ) : null}
                {resourceCounts.Observation ? (
                  <span className="inline-flex items-center gap-1 rounded-md bg-cyan-500/10 px-2 py-1 text-cyan-700 dark:text-cyan-300">
                    <FlaskConical className="h-3 w-3" />
                    Observation: {resourceCounts.Observation}
                  </span>
                ) : null}
              </div>
            </div>

            {/* Action Buttons: Copy & Download */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <FileCode className="h-4 w-4" />
                <span>Standard HL7 FHIR JSON Representation</span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleCopyJson}
                  className="h-8 gap-1.5 text-xs"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-600" />
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                      <span>Copy JSON</span>
                    </>
                  )}
                </Button>
                <Button
                  size="sm"
                  onClick={handleDownloadJson}
                  className="h-8 gap-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <Download className="h-3.5 w-3.5" />
                  <span>Download Bundle JSON</span>
                </Button>
              </div>
            </div>

            {/* Formatted JSON Inspector */}
            <div className="rounded-lg border border-border bg-muted/60 p-3">
              <pre className="max-h-80 overflow-auto font-mono text-[11px] leading-relaxed text-foreground select-all">
                {jsonString}
              </pre>
            </div>
          </div>
        ) : null}

        {/* Footer actions */}
        <div className="flex justify-end pt-2 border-t border-border">
          <Button variant="outline" size="sm" onClick={onClose} className="text-xs">
            Close
          </Button>
        </div>
      </div>
    </Dialog>
  );
}
