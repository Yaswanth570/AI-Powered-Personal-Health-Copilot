import { CalendarClock, FileText, FlaskConical, Pill, type LucideIcon } from "lucide-react";
import { buildSummaryCards } from "../../lib/records";
import type { MedicalRecord, SummaryCard } from "../../types";
import { Card } from "../ui/card";

const icons: Record<SummaryCard["icon"], LucideIcon> = {
  folder: FileText,
  flask: FlaskConical,
  pill: Pill,
  calendar: CalendarClock,
};

interface SummaryCardsProps {
  records: MedicalRecord[];
}

export function SummaryCards({ records }: SummaryCardsProps) {
  const cards = buildSummaryCards(records);

  return (
    <section aria-labelledby="summary-heading">
      <h2 id="summary-heading" className="sr-only">
        Sample summary counts
      </h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = icons[card.icon];
          return (
            <Card key={card.id} className="flex items-start gap-4">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-primary">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm text-muted-foreground">{card.label}</p>
                <p className="mt-1 font-display text-xl font-medium text-foreground">
                  {card.value}
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{card.detail}</p>
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
