import { demoBanner, navItems, productName } from "../../data/demoData";
import type { NavSection } from "../../types";
import { cn } from "../../lib/utils";
import { Logo } from "./Logo";
import { navIcons } from "./navIcons";

interface SidebarProps {
  active: NavSection;
  onNavigate: (section: NavSection) => void;
}

export function Sidebar({ active, onNavigate }: SidebarProps) {
  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-sidebar lg:flex">
      <div className="px-5 py-6">
        <Logo />
        <p className="sr-only">{productName}</p>
      </div>
      <nav className="flex-1 px-3" aria-label="Primary">
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
                    "flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left text-sm transition-colors",
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
      <p className="px-5 py-5 text-xs leading-5 text-muted-foreground">{demoBanner}</p>
    </aside>
  );
}
