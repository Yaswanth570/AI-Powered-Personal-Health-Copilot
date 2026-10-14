import { timelineEvents } from "../../data/demoData";
import { Card, CardDescription, CardHeader, CardTitle } from "../ui/card";

interface HealthTimelinePreviewProps {
  limit?: number;
}

export function HealthTimelinePreview({ limit }: HealthTimelinePreviewProps) {
  const events = limit ? timelineEvents.slice(0, limit) : timelineEvents;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Health timeline preview</CardTitle>
        <CardDescription>
          Chronological sample events. Dates and document types are fictional.
        </CardDescription>
      </CardHeader>
      <ol className="space-y-4">
        {events.map((event, index) => (
          <li key={event.id} className="flex gap-4">
            <div className="flex flex-col items-center">
              <span className="mt-1 h-2.5 w-2.5 rounded-full bg-primary" aria-hidden="true" />
              {index < events.length - 1 ? (
                <span className="mt-1 w-px flex-1 bg-border" aria-hidden="true" />
              ) : null}
            </div>
            <div className="pb-2">
              <p className="text-xs text-muted-foreground">{event.date}</p>
              <p className="mt-1 font-medium text-foreground">{event.title}</p>
              <p className="text-xs text-primary">{event.documentType}</p>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">{event.summary}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
