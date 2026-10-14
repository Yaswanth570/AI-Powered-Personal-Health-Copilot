import {
  Bell,
  ChevronDown,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "../../context/AuthContext";
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

function getInitials(name?: string): string {
  if (!name) return "HP";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function Header({
  section,
  searchQuery,
  onSearchChange,
  onOpenMobileNav,
}: HeaderProps) {
  const { user, logout } = useAuth();
  const searchId = useId();
  const notificationsId = useId();
  const profileMenuId = useId();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const profileMenuRef = useRef<HTMLDivElement>(null);
  const copy = pageCopy[section];

  const displayName = user?.full_name || demoProfile.displayName;
  const displayEmail = user?.email || "patient@healthcopilot.local";
  const userInitials = getInitials(displayName);

  useEffect(() => {
    function onPointerDown(event: MouseEvent) {
      const target = event.target as Node;
      if (
        notificationsRef.current &&
        !notificationsRef.current.contains(target)
      ) {
        setNotificationsOpen(false);
      }
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(target)
      ) {
        setProfileMenuOpen(false);
      }
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setNotificationsOpen(false);
        setProfileMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

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

          {/* Sample notifications */}
          <div className="relative" ref={notificationsRef}>
            <Button
              variant="icon"
              aria-label="Open demo notifications"
              aria-expanded={notificationsOpen}
              aria-controls={notificationsId}
              onClick={() => {
                setNotificationsOpen((open) => !open);
                setProfileMenuOpen(false);
              }}
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

          {/* Interactive Authenticated Account Menu */}
          <div className="relative" ref={profileMenuRef}>
            <button
              type="button"
              id="account-menu-button"
              onClick={() => {
                setProfileMenuOpen((prev) => !prev);
                setNotificationsOpen(false);
              }}
              aria-expanded={profileMenuOpen}
              aria-haspopup="menu"
              aria-controls={profileMenuId}
              aria-label={`Account menu for ${displayName}`}
              className="flex items-center gap-2 rounded-full border border-border bg-card p-1 text-left transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <div
                className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-primary"
                aria-hidden="true"
              >
                {userInitials}
              </div>
              <ChevronDown className="h-3.5 w-3.5 mr-1 text-muted-foreground" aria-hidden="true" />
            </button>

            {profileMenuOpen ? (
              <div
                id={profileMenuId}
                role="menu"
                aria-labelledby="account-menu-button"
                className="absolute right-0 z-30 mt-2 w-72 rounded-xl border border-border bg-card p-3 shadow-xl animate-in fade-in zoom-in-95 duration-100"
              >
                <div className="flex items-center gap-3 border-b border-border pb-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold text-primary">
                    {userInitials}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-foreground">
                      {displayName}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {displayEmail}
                    </p>
                  </div>
                </div>

                <div className="py-2.5">
                  <div className="flex items-center gap-2 rounded-md bg-accent/40 px-2.5 py-1.5 text-xs text-primary">
                    <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
                    <span className="font-medium">Active Verified Session</span>
                  </div>
                  {user?.id ? (
                    <p className="mt-2 truncate px-1 text-[11px] text-muted-foreground">
                      User ID: <span className="font-mono text-[10px]">{user.id}</span>
                    </p>
                  ) : null}
                </div>

                <div className="border-t border-border pt-2">
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setProfileMenuOpen(false);
                      logout();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-medium text-red-600 transition-colors hover:bg-red-50 hover:text-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Sign Out of Health Portal</span>
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </header>
  );
}
