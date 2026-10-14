import type { ReactNode } from "react";
import type { NavSection } from "../../types";
import { Header } from "./Header";
import { MobileNav } from "./MobileNav";
import { Sidebar } from "./Sidebar";

interface AppShellProps {
  section: NavSection;
  searchQuery: string;
  mobileNavOpen: boolean;
  onNavigate: (section: NavSection) => void;
  onSearchChange: (value: string) => void;
  onOpenMobileNav: () => void;
  onCloseMobileNav: () => void;
  children: ReactNode;
}

export function AppShell({
  section,
  searchQuery,
  mobileNavOpen,
  onNavigate,
  onSearchChange,
  onOpenMobileNav,
  onCloseMobileNav,
  children,
}: AppShellProps) {
  return (
    <div className="flex min-h-svh bg-background text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:text-sm focus:shadow-md"
      >
        Skip to main content
      </a>
      <Sidebar active={section} onNavigate={onNavigate} />
      <MobileNav
        open={mobileNavOpen}
        active={section}
        onNavigate={onNavigate}
        onClose={onCloseMobileNav}
      />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          section={section}
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
          onOpenMobileNav={onOpenMobileNav}
        />
        <main id="main-content" className="flex-1 px-4 py-6 sm:px-6" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
