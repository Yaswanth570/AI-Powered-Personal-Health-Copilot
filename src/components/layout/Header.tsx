import { Bell, Menu, Search } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { demoNotifications, demoProfile, pageCopy } from "../../data/demoData";
import type { NavSection } from "../../types";
import { Button } from "../ui/button";
import { Input } from "../ui/input";

interface HeaderProps {
  section: NavSection;
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onOpenMobileNav: () => void;
}

export function Header({
  section,
  searchQuery,
  onSearchChange,
  onOpenMobileNav,
}: HeaderProps) {
  const searchId = useId();
  const notificationsId = useId();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const copy = pageCopy[section];

  useEffect(() => {
    if (!notificationsOpen) {
      return;
    }

    function onPointerDown(event: MouseEvent) {
      if (
        notificationsRef.current &&
        !notificationsRef.current.contains(event.target as Node)
      ) {
        setNotificationsOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
      }
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [notificationsOpen]);

  return (
    <header className="border-b border-border bg-card/80 px-4 py-4 backdrop-blur sm:px-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <Button
            variant="icon"
            className="mt-0.5 lg:hidden"
            onClick={onOpenMobileNav}
            aria-label="Open navigation"
          >
            <Menu className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="font-display text-2xl font-medium tracking-tight text-foreground">
              {copy.title}
            </h1>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">{copy.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <div className="relative min-w-0 flex-1 lg:w-72 lg:flex-none">
            <label htmlFor={searchId} className="sr-only">
              Search sample medical records
            </label>
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id={searchId}
              type="search"
              value={searchQuery}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search sample records"
              autoComplete="off"
              className="pl-9"
            />
          </div>

          <div className="relative" ref={notificationsRef}>
            <Button
              variant="icon"
              aria-label="Open demo notifications"
              aria-expanded={notificationsOpen}
              aria-controls={notificationsId}
              onClick={() => setNotificationsOpen((open) => !open)}
            >
              <Bell className="h-4 w-4" />
            </Button>
            {notificationsOpen ? (
              <div
                id={notificationsId}
                role="region"
                aria-label="Demo notifications"
                className="absolute right-0 z-20 mt-2 w-72 rounded-xl border border-border bg-card p-3 shadow-lg"
              >
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Sample notices
                </p>
                <ul className="space-y-3">
                  {demoNotifications.map((item) => (
                    <li key={item.id}>
                      <p className="text-sm font-medium text-foreground">{item.title}</p>
                      <p className="text-xs leading-5 text-muted-foreground">{item.body}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{item.time}</p>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>

          <div
            className="flex h-10 w-10 items-center justify-center rounded-full bg-accent text-sm font-medium text-primary"
            title={demoProfile.displayName}
            aria-label={`Demo profile: ${demoProfile.displayName}`}
          >
            {demoProfile.initials}
          </div>
        </div>
      </div>
    </header>
  );
}
