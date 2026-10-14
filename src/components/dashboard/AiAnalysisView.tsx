import {
  AlertCircle,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  FileQuestion,
  FileText,
  FlaskConical,
  Globe,
  Info,
  Loader2,
  Pill,
  Quote,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  User,
} from "lucide-react";
import { useState } from "react";
import { explainExtractionInTelugu } from "../../lib/persistenceApi";
import type { MedicalDocumentExtraction, TeluguHealthSummary } from "../../types";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

interface AiAnalysisViewProps {
  extraction: MedicalDocumentExtraction;
}

export function AiAnalysisView({ extraction }: AiAnalysisViewProps) {
  const [language, setLanguage] = useState<"en" | "te">("en");
  const [teluguSummary, setTeluguSummary] = useState<TeluguHealthSummary | null>(null);
  const [isLoadingTelugu, setIsLoadingTelugu] = useState(false);
  const [teluguError, setTeluguError] = useState<string | null>(null);

  const confidenceTone =
    extraction.confidence === "high"
      ? ("calm" as const)
      : extraction.confidence === "medium"
        ? ("neutral" as const)
        : ("warn" as const);

  const handleSelectLanguage = async (nextLang: "en" | "te") => {
    setLanguage(nextLang);
    if (nextLang === "te" && !teluguSummary && !isLoadingTelugu) {
      await fetchTeluguExplanation();
    }
  };

  const fetchTeluguExplanation = async () => {
    setIsLoadingTelugu(true);
    setTeluguError(null);
    try {
      const result = await explainExtractionInTelugu(extraction);
      setTeluguSummary(result);
    } catch (err) {
      setTeluguError(
        err instanceof Error
          ? err.message
          : "Failed to generate Telugu health explanation. Please check backend connection.",
      );
    } finally {
      setIsLoadingTelugu(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Bar with Language Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-card p-3 shadow-xs">
        <div className="flex items-center gap-2">
          <Globe className="h-4 w-4 text-primary" aria-hidden="true" />
          <span className="text-sm font-semibold text-foreground">
            Analysis Language / భాష ఎంపిక:
          </span>
          <span className="text-xs text-muted-foreground">
            {language === "en" ? "English (Default)" : "తెలుగు (Patient-Friendly Summary)"}
          </span>
        </div>

        {/* Segmented Language Toggle */}
        <div
          role="radiogroup"
          aria-label="Language selection"
          className="inline-flex items-center rounded-lg border border-border bg-muted/60 p-1 text-xs"
        >
          <button
            type="button"
            role="radio"
            aria-checked={language === "en"}
            onClick={() => handleSelectLanguage("en")}
            className={`rounded-md px-3 py-1 font-medium transition-all ${
              language === "en"
                ? "bg-background text-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            English
          </button>
          <button
            type="button"
            role="radio"
            aria-checked={language === "te"}
            onClick={() => handleSelectLanguage("te")}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-medium transition-all ${
              language === "te"
                ? "bg-primary text-primary-foreground shadow-xs"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <span>తెలుగు (Telugu)</span>
            {isLoadingTelugu ? (
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
            ) : null}
          </button>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* TELUGU VIEW                                                               */}
      {/* ========================================================================= */}
      {language === "te" ? (
        <div className="space-y-6">
          {/* Mandatory Clinical Safety Disclaimer Banner (Telugu & English) */}
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-900 dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-200">
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
              <div className="space-y-1.5 text-sm leading-relaxed">
                <p className="font-semibold text-amber-950 dark:text-amber-100">
                  వైద్య సమాచార వివరణ — వైద్యుని ధ్రువీకరణ తప్పనిసరి (Patient Awareness Only)
                </p>
                <p className="text-xs sm:text-sm font-medium">
                  {teluguSummary?.disclaimer_telugu ||
                    "ఈ సమాచారం కేవలం రోగి అవగాహన కొరకు మాత్రమే. ఇది వైద్య నిర్ధారణ లేదా చికిత్స సలహా కాదు. ఎల్లప్పుడూ మీ వైద్యుడిని సంప్రదించండి."}
                </p>
                <p className="text-xs text-amber-800/80 dark:text-amber-300/80 border-t border-amber-500/20 pt-1.5 mt-1">
                  Original Safety Rule: {extraction.disclaimer} Always compare clinical values and prescriptions against original hospital reports.
                </p>
              </div>
            </div>
          </div>

          {/* Loading Telugu Explanation */}
          {isLoadingTelugu ? (
            <div className="flex flex-col items-center justify-center rounded-lg border border-border bg-card py-16 text-center space-y-3 shadow-xs">
              <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
              <div className="space-y-1">
                <p className="text-sm font-semibold text-foreground">
                  రోగికి అర్థమయ్యే తెలుగులో వివరణను రూపొందిస్తున్నాము…
                </p>
                <p className="text-xs text-muted-foreground max-w-md mx-auto">
                  Generating Telugu explanation with Gemini AI. Preserving exact medicine names, dosages, laboratory numbers, and source evidence.
                </p>
              </div>
            </div>
          ) : null}

          {/* Error Generating Telugu */}
          {teluguError && !isLoadingTelugu ? (
            <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-red-950 dark:text-red-100 space-y-3">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" aria-hidden="true" />
                <div>
                  <p className="text-xs font-semibold">తెలుగు వివరణ పొందడంలో సమస్య ఏర్పడింది (Telugu Generation Error)</p>
                  <p className="text-xs text-red-800 dark:text-red-200 mt-1">{teluguError}</p>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setLanguage("en")}
                  className="text-xs"
                >
                  View English Extraction
                </Button>
                <Button
                  size="sm"
                  onClick={fetchTeluguExplanation}
                  className="gap-1.5 text-xs bg-primary text-primary-foreground hover:bg-primary/90"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  మళ్ళీ ప్రయత్నించండి (Retry)
                </Button>
              </div>
            </div>
          ) : null}

          {/* Telugu Summary Content */}
          {teluguSummary && !isLoadingTelugu ? (
            <div className="space-y-6">
              {/* Overall Patient Summary in Telugu */}
              <div className="rounded-lg border border-border bg-card p-4 shadow-xs space-y-2">
                <div className="flex items-center justify-between border-b border-border pb-2.5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
                    <h4 className="text-sm font-semibold text-foreground">
                      మొత్తం ఆరోగ్య సారాంశం (Overall Health Summary)
                    </h4>
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    Powered by {teluguSummary.model_used}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-foreground/90 font-normal">
                  {teluguSummary.overall_summary_telugu}
                </p>
              </div>

              {/* Telugu Diagnoses Section */}
              <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <Stethoscope className="h-4 w-4 text-primary" aria-hidden="true" />
                    <h4 className="text-sm font-semibold text-foreground">
                      రోగనిర్ధారణలు & విశ్లేషణ (Diagnoses & Findings)
                    </h4>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {teluguSummary.diagnoses_explanations.length} అంశాలు (items)
                  </span>
                </div>

                {teluguSummary.diagnoses_explanations.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {teluguSummary.diagnoses_explanations.map((diag, idx) => (
                      <div
                        key={idx}
                        className="rounded-md border border-border bg-background p-3.5 space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div>
                            <span className="text-xs font-semibold text-primary block">
                              {diag.telugu_term || diag.original_diagnosis || diag.diagnosis}
                            </span>
                            <span className="text-xs font-mono text-muted-foreground">
                              Original Diagnosis: {diag.diagnosis || diag.original_diagnosis}
                            </span>
                          </div>
                          <Badge tone="calm" className="text-[11px]">
                            మూల పత్రం నుండి (Source Record)
                          </Badge>
                        </div>

                        <p className="text-xs leading-relaxed text-foreground">
                          {diag.telugu_explanation}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
                    ఈ పత్రంలో ఎటువంటి నిర్దిష్ట వ్యాధి నిర్ధారణలు పేర్కొనబడలేదు.
                  </p>
                )}
              </div>

              {/* Telugu Medicines Section */}
              <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <Pill className="h-4 w-4 text-primary" aria-hidden="true" />
                    <h4 className="text-sm font-semibold text-foreground">
                      సూచించిన మందులు & రోగి సూచనలు (Prescribed Medicines & Instructions)
                    </h4>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {teluguSummary.medicines_explanations.length} మందులు
                  </span>
                </div>

                {teluguSummary.medicines_explanations.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {teluguSummary.medicines_explanations.map((med, idx) => (
                      <div
                        key={idx}
                        className="rounded-md border border-border bg-background p-3.5 space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-semibold text-sm text-foreground">
                            {med.name}
                          </span>
                          <div className="flex flex-wrap items-center gap-1.5 font-mono text-xs">
                            {med.dose ? (
                              <Badge tone="neutral">{med.dose}</Badge>
                            ) : null}
                            {med.frequency ? (
                              <Badge tone="calm">{med.frequency}</Badge>
                            ) : null}
                            {med.duration ? (
                              <Badge tone="neutral">{med.duration}</Badge>
                            ) : null}
                          </div>
                        </div>

                        <div className="rounded bg-muted/40 p-2.5 text-xs text-foreground/90 leading-relaxed">
                          <span className="font-semibold text-primary block mb-0.5">
                            ఉపయోగం & వాడే విధానం:
                          </span>
                          {med.telugu_purpose_and_instructions}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
                    ఈ పత్రంలో మందుల వివరాలు ఏవీ లేవు.
                  </p>
                )}
              </div>

              {/* Telugu Lab Investigations Section */}
              <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <FlaskConical className="h-4 w-4 text-primary" aria-hidden="true" />
                    <h4 className="text-sm font-semibold text-foreground">
                      ల్యాబ్ పరీక్షల ఫలితాలు & వివరణ (Laboratory Results & Meaning)
                    </h4>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {teluguSummary.labs_explanations.length} పరీక్షలు
                  </span>
                </div>

                {teluguSummary.labs_explanations.length > 0 ? (
                  <div className="mt-3 space-y-3">
                    {teluguSummary.labs_explanations.map((lab, idx) => {
                      const isAbnormal = lab.abnormal_flag === true;
                      return (
                        <div
                          key={idx}
                          className={`rounded-md border p-3.5 space-y-2 ${
                            isAbnormal
                              ? "border-amber-500/40 bg-amber-500/5"
                              : "border-border bg-background"
                          }`}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="font-medium text-xs text-foreground">
                              {lab.test_name}
                            </span>
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-semibold text-sm">
                                {lab.value ?? "—"}{" "}
                                {lab.unit ? (
                                  <span className="text-xs text-muted-foreground">{lab.unit}</span>
                                ) : null}
                              </span>
                              {isAbnormal ? (
                                <Badge tone="warn" className="text-[10px]">
                                  పరిధికి మించి (Abnormal)
                                </Badge>
                              ) : (
                                <Badge tone="calm" className="text-[10px]">
                                  సాధారణం (Normal)
                                </Badge>
                              )}
                            </div>
                          </div>

                          {lab.reference_range ? (
                            <div className="text-[11px] text-muted-foreground font-mono">
                              సాధారణ పరిధి (Normal Range): {lab.reference_range}
                            </div>
                          ) : null}

                          <p className="text-xs leading-relaxed text-foreground/90">
                            {lab.telugu_status_and_meaning || lab.telugu_explanation}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-3 rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
                    ఈ పత్రంలో ఎటువంటి ల్యాబ్ పరీక్షల ఫలితాలు లేవు.
                  </p>
                )}
              </div>

              {/* Telugu Fidelity Guarantee Banner */}
              <div className="rounded-lg border border-border bg-muted/40 p-3.5 text-xs text-muted-foreground flex items-start gap-2.5">
                <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  <strong>ఖచ్చితత్వ హామీ:</strong> మందుల పేర్లు, మోతాదులు (Dosage), సంఖ్యా రీడింగ్‌లు మరియు నివేదిక తేదీలు మూల పత్రంలో పేర్కొన్నట్లే యథాతథంగా ఉంచబడ్డాయి. AI స్వంతంగా ఎటువంటి కొత్త రోగనిర్ధారణలను లేదా చికిత్సా సలహాలను జోడించదు.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* ========================================================================= */}
      {/* ENGLISH VIEW (DEFAULT)                                                    */}
      {/* ========================================================================= */}
      {language === "en" ? (
        <div className="space-y-6">
          {/* Mandatory Clinical Safety Disclaimer Banner */}
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-900 dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-200">
            <div className="flex items-start gap-3">
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" aria-hidden="true" />
              <div className="space-y-1 text-sm leading-relaxed">
                <p className="font-semibold text-amber-950 dark:text-amber-100">
                  AI-Extracted Clinical Information — Verification Required
                </p>
                <p className="text-xs sm:text-sm">
                  {extraction.disclaimer} Always compare extracted values, dosages, and diagnoses against the
                  original physical or digital document. AI outputs must never be treated as verified medical
                  facts or clinical diagnoses.
                </p>
              </div>
            </div>
          </div>

          {/* Document & Patient Demographics Overview */}
          <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" aria-hidden="true" />
                <span className="text-sm font-semibold text-foreground">Extracted Metadata</span>
                <span className="text-xs text-muted-foreground">· Powered by {extraction.model_used}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">Confidence:</span>
                <Badge tone={confidenceTone}>
                  {extraction.confidence.toUpperCase()}
                </Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 text-sm">
              <div>
                <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                  <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                  Document Type
                </span>
                <p className="mt-1 font-medium text-foreground">
                  {extraction.document_type || (
                    <span className="italic text-muted-foreground">Not mentioned in document</span>
                  )}
                </p>
              </div>

              <div>
                <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                  <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                  Report / Encounter Date
                </span>
                <p className="mt-1 font-medium text-foreground">
                  {extraction.report_date ? (
                    extraction.report_date
                  ) : (
                    <Badge tone="warn" className="text-[11px] font-normal">
                      Not mentioned
                    </Badge>
                  )}
                </p>
              </div>

              <div>
                <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                  <User className="h-3.5 w-3.5" aria-hidden="true" />
                  Patient Name
                </span>
                <p className="mt-1 font-medium text-foreground">
                  {extraction.patient_name ? (
                    <span className="font-semibold text-foreground">{extraction.patient_name}</span>
                  ) : (
                    <Badge tone="warn" className="text-[11px] font-normal">
                      Not explicitly mentioned
                    </Badge>
                  )}
                </p>
              </div>

              <div>
                <span className="text-xs font-medium text-muted-foreground">Age & Gender</span>
                <p className="mt-1 text-foreground">
                  {extraction.patient_age || extraction.patient_gender ? (
                    `${extraction.patient_age ?? "Age unspecified"} · ${extraction.patient_gender ?? "Gender unspecified"}`
                  ) : (
                    <span className="italic text-muted-foreground">Not mentioned</span>
                  )}
                </p>
              </div>

              {extraction.confidence_reason ? (
                <div className="sm:col-span-2">
                  <span className="text-xs font-medium text-muted-foreground">Extraction Assessment</span>
                  <p className="mt-1 text-xs text-muted-foreground leading-normal">
                    {extraction.confidence_reason}
                  </p>
                </div>
              ) : null}
            </div>

            {extraction.summary ? (
              <div className="mt-4 rounded-md bg-muted/40 p-3 text-xs leading-relaxed text-muted-foreground">
                <span className="font-medium text-foreground">Summary: </span>
                {extraction.summary}
              </div>
            ) : null}
          </div>

          {/* Diagnoses Section */}
          <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Stethoscope className="h-4 w-4 text-primary" aria-hidden="true" />
                <h4 className="text-sm font-semibold text-foreground">Explicit Diagnoses & Clinical Findings</h4>
              </div>
              <span className="text-xs text-muted-foreground">
                {extraction.diagnoses.length} recorded
              </span>
            </div>

            {extraction.diagnoses.length > 0 ? (
              <div className="mt-3 space-y-3">
                {extraction.diagnoses.map((diag, idx) => (
                  <div
                    key={idx}
                    className="rounded-md border border-border bg-background p-3 transition-colors hover:border-border/80"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-foreground">{diag.diagnosis}</p>
                      <div className="flex items-center gap-2">
                        {diag.status ? (
                          <Badge tone="calm">{diag.status}</Badge>
                        ) : null}
                        {diag.page_number ? (
                          <span className="text-[11px] text-muted-foreground">Page {diag.page_number}</span>
                        ) : null}
                      </div>
                    </div>
                    {diag.evidence ? (
                      <div className="mt-2 flex items-start gap-1.5 text-xs text-muted-foreground">
                        <Quote className="h-3 w-3 shrink-0 text-muted-foreground/70" aria-hidden="true" />
                        <span className="italic">“{diag.evidence}”</span>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
                No explicit diagnoses documented in source text.
                <p className="mt-0.5 text-[11px] text-muted-foreground/80">
                  (Clinical safety rule: diagnoses are never inferred from lab test values)
                </p>
              </div>
            )}
          </div>

          {/* Prescribed Medicines Section */}
          <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Pill className="h-4 w-4 text-primary" aria-hidden="true" />
                <h4 className="text-sm font-semibold text-foreground">Prescribed Medicines</h4>
              </div>
              <span className="text-xs text-muted-foreground">
                {extraction.medicines.length} item{extraction.medicines.length === 1 ? "" : "s"}
              </span>
            </div>

            {extraction.medicines.length > 0 ? (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[32rem] text-left text-xs">
                  <thead className="border-b border-border text-muted-foreground uppercase tracking-wider text-[10px]">
                    <tr>
                      <th scope="col" className="py-2 pr-3 font-semibold">Medication Name</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Dose & Route</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Frequency</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Duration</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Instructions</th>
                      <th scope="col" className="py-2 font-semibold">Source Evidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {extraction.medicines.map((med, idx) => (
                      <tr key={idx} className="hover:bg-muted/30">
                        <td className="py-2.5 pr-3 font-medium text-foreground">
                          {med.name}
                        </td>
                        <td className="py-2.5 pr-3 text-muted-foreground">
                          {med.dose || "—"}
                          {med.route ? ` (${med.route})` : ""}
                        </td>
                        <td className="py-2.5 pr-3 text-foreground font-mono">
                          {med.frequency ? (
                            <Badge tone="neutral" className="text-[11px]">
                              {med.frequency}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-2.5 pr-3 text-muted-foreground">
                          {med.duration || "—"}
                        </td>
                        <td className="py-2.5 pr-3 text-muted-foreground">
                          {med.instructions || "—"}
                        </td>
                        <td className="py-2.5 text-muted-foreground">
                          {med.evidence ? (
                            <span className="italic line-clamp-1" title={med.evidence}>
                              “{med.evidence}”
                            </span>
                          ) : (
                            "—"
                          )}
                          {med.page_number ? (
                            <span className="block text-[10px] text-muted-foreground/70">
                              Pg {med.page_number}
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-3 rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
                No medications mentioned in source text.
              </p>
            )}
          </div>

          {/* Laboratory Investigations Section */}
          <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FlaskConical className="h-4 w-4 text-primary" aria-hidden="true" />
                <h4 className="text-sm font-semibold text-foreground">Laboratory Tests & Values</h4>
              </div>
              <span className="text-xs text-muted-foreground">
                {extraction.lab_tests.length} result{extraction.lab_tests.length === 1 ? "" : "s"}
              </span>
            </div>

            {extraction.lab_tests.length > 0 ? (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[32rem] text-left text-xs">
                  <thead className="border-b border-border text-muted-foreground uppercase tracking-wider text-[10px]">
                    <tr>
                      <th scope="col" className="py-2 pr-3 font-semibold">Test Name</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Value</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Reference Range</th>
                      <th scope="col" className="py-2 pr-3 font-semibold">Flag</th>
                      <th scope="col" className="py-2 font-semibold">Source Evidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {extraction.lab_tests.map((lab, idx) => {
                      const isAbnormal = lab.abnormal_flag === true;
                      const isNormal = lab.abnormal_flag === false;
                      return (
                        <tr key={idx} className={isAbnormal ? "bg-amber-500/5 hover:bg-amber-500/10" : "hover:bg-muted/30"}>
                          <td className="py-2.5 pr-3 font-medium text-foreground">
                            {lab.test_name}
                          </td>
                          <td className="py-2.5 pr-3">
                            <span className={`font-mono font-semibold ${isAbnormal ? "text-amber-700 dark:text-amber-400" : "text-foreground"}`}>
                              {lab.value ?? "—"}
                            </span>
                            {lab.unit ? <span className="ml-1 text-muted-foreground">{lab.unit}</span> : null}
                          </td>
                          <td className="py-2.5 pr-3 text-muted-foreground font-mono">
                            {lab.reference_range ?? "—"}
                          </td>
                          <td className="py-2.5 pr-3">
                            {isAbnormal ? (
                              <Badge tone="warn" className="text-[10px] font-semibold">
                                Abnormal / Outside Range
                              </Badge>
                            ) : isNormal ? (
                              <Badge tone="calm" className="text-[10px]">
                                Normal
                              </Badge>
                            ) : (
                              <span className="text-muted-foreground text-[11px]">—</span>
                            )}
                          </td>
                          <td className="py-2.5 text-muted-foreground">
                            {lab.evidence ? (
                              <span className="italic line-clamp-1" title={lab.evidence}>
                                “{lab.evidence}”
                              </span>
                            ) : (
                              "—"
                            )}
                            {lab.page_number ? (
                              <span className="block text-[10px] text-muted-foreground/70">
                                Pg {lab.page_number}
                              </span>
                            ) : null}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-3 rounded-md border border-dashed border-border py-4 text-center text-xs text-muted-foreground">
                No laboratory test results mentioned in source text.
              </p>
            )}
          </div>

          {/* Missing Fields and Uncertainties Section */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Missing Fields */}
            <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
              <div className="flex items-center gap-2 border-b border-border pb-2.5">
                <FileQuestion className="h-4 w-4 text-amber-500" aria-hidden="true" />
                <h4 className="text-xs font-semibold text-foreground">Expected Fields Missing from Source</h4>
              </div>
              {extraction.missing_fields.length > 0 ? (
                <ul className="mt-2.5 space-y-1.5 text-xs">
                  {extraction.missing_fields.map((field, idx) => (
                    <li key={idx} className="flex items-start gap-1.5 text-muted-foreground">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-amber-500 shrink-0" aria-hidden="true" />
                      <span>{field}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-2.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                  <span>All standard document fields were explicitly accounted for.</span>
                </div>
              )}
            </div>

            {/* Uncertainties & OCR artifacts */}
            <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
              <div className="flex items-center gap-2 border-b border-border pb-2.5">
                <AlertTriangle className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <h4 className="text-xs font-semibold text-foreground">Ambiguities & Source Notes</h4>
              </div>
              {extraction.uncertainties.length > 0 ? (
                <ul className="mt-2.5 space-y-1.5 text-xs">
                  {extraction.uncertainties.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-1.5 text-muted-foreground">
                      <Info className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" aria-hidden="true" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="mt-2.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
                  <span>No illegible text, handwritten ambiguities, or OCR artifacts noted.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
