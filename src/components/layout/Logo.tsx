import { productName } from "../../data/demoData";
import { cn } from "../../lib/utils";

interface LogoProps {
  compact?: boolean;
  className?: string;
}

export function Logo({ compact = false, className }: LogoProps) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span
        className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground"
        aria-hidden="true"
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none">
          <path
            d="M12 4.5c-2.2 3.1-6 4.4-6 8.2A6 6 0 0 0 12 18.7a6 6 0 0 0 6-5.99c0-3.8-3.8-5.11-6-8.21Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinejoin="round"
          />
          <path
            d="M12 10.2v4.2M9.9 12.3h4.2"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </span>
      {compact ? (
        <span className="sr-only">{productName}</span>
      ) : (
        <span className="leading-tight">
          <span className="block font-display text-base font-medium text-foreground">
            Personal Health
          </span>
          <span className="block text-xs tracking-wide text-muted-foreground">Copilot</span>
        </span>
      )}
    </div>
  );
}
