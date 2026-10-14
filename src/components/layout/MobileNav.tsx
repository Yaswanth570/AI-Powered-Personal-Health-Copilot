import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { navItems } from "../../data/demoData";
import { cn } from "../../lib/utils";
import type { NavSection } from "../../types";
import { Button } from "../ui/button";
import { Logo } from "./Logo";
import { navIcons } from "./navIcons";

interface MobileNavProps {
  open: boolean;
  active: NavSection;
  onNavigate: (section: NavSection) => void;
  onClose: () => void;
}

export function MobileNav({ open, active, onNavigate, onClose }: MobileNavProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-foreground/30"
        aria-label="Close navigation"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
        className="absolute inset-y-0 left-0 flex w-72 flex-col bg-sidebar shadow-xl"
      >
        <div className="flex items-center justify-between px-4 py-4">
          <Logo />
          <Button
            ref={closeButtonRef}
            variant="ghost"
            className="h-9 w-9 p-0"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <nav className="px-3" aria-label="Mobile primary">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = navIcons[item.id];
              const isActive = item.id === active;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onNavigate(item.id)}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                      isActive
                        ? "bg-accent font-medium text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground",
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </div>
  );
}
