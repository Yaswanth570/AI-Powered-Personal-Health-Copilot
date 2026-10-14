import {
  CalendarClock,
  FileText,
  FlaskConical,
  LayoutDashboard,
  Pill,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { NavSection } from "../../types";

export const navIcons: Record<NavSection, LucideIcon> = {
  overview: LayoutDashboard,
  "health-ai": Sparkles,
  records: FileText,
  labs: FlaskConical,
  prescriptions: Pill,
  timeline: CalendarClock,
  settings: Settings,
};
