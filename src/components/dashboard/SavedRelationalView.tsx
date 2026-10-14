import {
  FileText,
  FlaskConical,
  Pill,
  Stethoscope,
} from "lucide-react";
import type { SavedMedicalDocument } from "../../types";
import { Badge } from "../ui/badge";

interface SavedRelationalViewProps {
  document: SavedMedicalDocument;
}

export function SavedRelationalView({ document }: SavedRelationalViewProps) {
  const diagnoses = document.diagnoses || [];
  const medications = document.medications || [];
  const labs = document.lab_results || [];

  return (
    <div className="space-y-6">
      {/* Relational Diagnoses */}
      <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <Stethoscope className="h-4 w-4 text-primary" aria-hidden="true" />
          <h4 className="text-sm font-semibold text-foreground">
            Persisted Diagnoses & Clinical Findings
          </h4>
          <span className="text-xs text-muted-foreground">({diagnoses.length})</span>
        </div>
        {diagnoses.length > 0 ? (
          <ul className="mt-3 divide-y divide-border text-sm">
            {diagnoses.map((d) => (
              <li key={d.id} className="py-2.5 first:pt-1 last:pb-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-foreground">{d.diagnosis}</span>
                  {d.status ? (
                    <Badge tone="neutral" className="text-xs capitalize">
                      {d.status}
                    </Badge>
                  ) : null}
                </div>
                {d.evidence ? (
                  <p className="mt-1 text-xs text-muted-foreground italic">
                    “{d.evidence}”
                    {d.page_number ? ` · Page ${d.page_number}` : ""}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground italic">
            No distinct diagnoses were recorded for this document.
          </p>
        )}
      </div>

      {/* Relational Medications */}
      <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <Pill className="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          <h4 className="text-sm font-semibold text-foreground">
            Prescribed Medications & Regimens
          </h4>
          <span className="text-xs text-muted-foreground">({medications.length})</span>
        </div>
        {medications.length > 0 ? (
          <ul className="mt-3 divide-y divide-border text-sm">
            {medications.map((m) => (
              <li key={m.id} className="py-2.5 first:pt-1 last:pb-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-foreground">{m.name}</span>
                  <div className="flex flex-wrap items-center gap-1.5 text-xs">
                    {m.dose ? <Badge tone="calm">{m.dose}</Badge> : null}
                    {m.frequency ? <Badge tone="neutral">{m.frequency}</Badge> : null}
                    {m.duration ? <span className="text-muted-foreground">for {m.duration}</span> : null}
                  </div>
                </div>
                {m.instructions ? (
                  <p className="mt-1 text-xs text-foreground/80 font-normal">
                    Instructions: {m.instructions}
                  </p>
                ) : null}
                {m.evidence ? (
                  <p className="mt-0.5 text-xs text-muted-foreground italic">
                    “{m.evidence}”
                    {m.page_number ? ` · Page ${m.page_number}` : ""}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground italic">
            No prescribed medications recorded for this document.
          </p>
        )}
      </div>

      {/* Relational Lab Results */}
      <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <FlaskConical className="h-4 w-4 text-indigo-500" aria-hidden="true" />
          <h4 className="text-sm font-semibold text-foreground">
            Laboratory Investigations & Biomarkers
          </h4>
          <span className="text-xs text-muted-foreground">({labs.length})</span>
        </div>
        {labs.length > 0 ? (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border text-muted-foreground uppercase tracking-wider">
                <tr>
                  <th className="py-2 pr-3 font-medium">Investigation</th>
                  <th className="py-2 pr-3 font-medium">Result Value</th>
                  <th className="py-2 pr-3 font-medium">Ref Range</th>
                  <th className="py-2 font-medium">Flag</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {labs.map((l) => (
                  <tr key={l.id}>
                    <td className="py-2 pr-3 font-medium text-foreground">
                      {l.test_name}
                      {l.evidence ? (
                        <p className="text-[11px] text-muted-foreground italic font-normal">
                          “{l.evidence}”
                        </p>
                      ) : null}
                    </td>
                    <td className="py-2 pr-3 text-foreground font-mono">
                      {l.value ?? "—"} {l.unit ?? ""}
                    </td>
                    <td className="py-2 pr-3 text-muted-foreground">
                      {l.reference_range ?? "—"}
                    </td>
                    <td className="py-2">
                      {l.abnormal_flag === true ? (
                        <Badge tone="warn" className="text-[10px]">
                          ABNORMAL
                        </Badge>
                      ) : l.abnormal_flag === false ? (
                        <Badge tone="calm" className="text-[10px]">
                          NORMAL
                        </Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-3 text-xs text-muted-foreground italic">
            No laboratory test results recorded for this document.
          </p>
        )}
      </div>

      {/* Raw Text View */}
      {document.raw_text ? (
        <div className="rounded-lg border border-border bg-card p-4 shadow-xs">
          <div className="flex items-center gap-2 border-b border-border pb-3">
            <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            <h4 className="text-sm font-semibold text-foreground">
              Stored Extracted Text
            </h4>
            <span className="text-xs text-muted-foreground">
              ({document.total_char_count.toLocaleString()} characters)
            </span>
          </div>
          <pre className="mt-3 max-h-60 overflow-auto whitespace-pre-wrap break-words rounded bg-muted/40 p-3 font-sans text-xs leading-5 text-foreground">
            {document.raw_text}
          </pre>
        </div>
      ) : null}
    </div>
  );
}
