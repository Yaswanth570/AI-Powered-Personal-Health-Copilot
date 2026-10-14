import { ArrowRight, Upload } from "lucide-react";
import { Button } from "../ui/button";

interface WelcomeSectionProps {
  onUpload: () => void;
  onExplore: () => void;
}

export function WelcomeSection({ onUpload, onExplore }: WelcomeSectionProps) {
  return (
    <section className="rounded-xl border border-border bg-card px-6 py-7 shadow-[0_1px_2px_rgba(28,42,40,0.04)]">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-primary">
        Synthetic demo workspace
      </p>
      <h2 className="mt-3 max-w-2xl font-display text-3xl font-medium tracking-tight text-foreground sm:text-4xl">
        Your health, clearly understood.
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
        Personal Health Copilot is being designed to help you keep medical files in one place,
        read laboratory results in plain language, and follow prescriptions over time. This
        screen uses labelled sample content only. You can list PDF and image files in this
        browser session; they are not saved and are not analyzed.
      </p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Button onClick={onUpload}>
          <Upload className="h-4 w-4" aria-hidden="true" />
          Upload Medical Record
        </Button>
        <Button variant="secondary" onClick={onExplore}>
          Explore Dashboard
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </section>
  );
}
