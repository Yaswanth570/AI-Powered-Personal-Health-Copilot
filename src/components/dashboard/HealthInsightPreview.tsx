import { labInsight } from "../../data/demoData";
import { Badge } from "../ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "../ui/card";

export function HealthInsightPreview() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Health insights preview</CardTitle>
        <CardDescription>
          A single synthetic laboratory result. This is educational copy, not a clinical
          interpretation.
        </CardDescription>
      </CardHeader>
      <div className="rounded-lg border border-border bg-muted/60 p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {labInsight.panelName}
        </p>
        <div className="mt-3 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm text-muted-foreground">Test name</p>
            <p className="font-display text-2xl font-medium text-foreground">
              {labInsight.testName}
            </p>
          </div>
          <p className="font-display text-3xl font-medium text-foreground">
            {labInsight.value}
            <span className="ml-1 text-base font-sans font-normal text-muted-foreground">
              {labInsight.unit}
            </span>
          </p>
        </div>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">Sample reference range</dt>
            <dd className="mt-1 leading-6">{labInsight.sampleReferenceRange}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Status indicator</dt>
            <dd className="mt-1">
              <Badge tone="neutral">{labInsight.statusLabel}</Badge>
            </dd>
          </div>
        </dl>
      </div>
      <p className="mt-4 text-sm leading-6 text-muted-foreground">{labInsight.educationalNote}</p>
    </Card>
  );
}
