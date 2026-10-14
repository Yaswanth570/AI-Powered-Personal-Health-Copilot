import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function filterRecords<T extends { name: string; type: string; status: string }>(
  records: T[],
  query: string,
): T[] {
  const needle = query.trim().toLowerCase();
  if (!needle) {
    return records;
  }

  return records.filter((record) => {
    return (
      record.name.toLowerCase().includes(needle) ||
      record.type.toLowerCase().includes(needle) ||
      record.status.toLowerCase().includes(needle)
    );
  });
}
