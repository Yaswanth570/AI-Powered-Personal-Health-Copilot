export const MAX_FILE_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"] as const;
export const ACCEPTED_FILE_INPUT = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

const acceptedExtensionSet = new Set<string>(ACCEPTED_EXTENSIONS);

export type FileValidationResult =
  | { ok: true }
  | { ok: false; message: string };

export function getFileExtension(filename: string): string {
  const separator = filename.lastIndexOf(".");
  if (separator < 0 || separator === filename.length - 1) {
    return "";
  }
  return filename.slice(separator).toLowerCase();
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    const kilobytes = bytes / 1024;
    return `${kilobytes < 10 ? kilobytes.toFixed(1) : Math.round(kilobytes)} KB`;
  }
  const megabytes = bytes / (1024 * 1024);
  return `${megabytes < 10 ? megabytes.toFixed(1) : Math.round(megabytes)} MB`;
}

export function formatIndianDate(date: Date = new Date()): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function validateFile(file: File): FileValidationResult {
  if (file.size === 0) {
    return {
      ok: false,
      message: `“${file.name}” is empty (0 bytes) and cannot be added.`,
    };
  }

  const extension = getFileExtension(file.name);
  if (!acceptedExtensionSet.has(extension)) {
    return {
      ok: false,
      message: `“${file.name}” is not a supported type. Choose a PDF, JPG, JPEG, or PNG file.`,
    };
  }

  if (file.size > MAX_FILE_BYTES) {
    return {
      ok: false,
      message: `“${file.name}” is ${formatFileSize(file.size)}, which is larger than the 10 MB limit.`,
    };
  }

  return { ok: true };
}

export function isSameFile(left: File, right: File): boolean {
  return (
    left.name === right.name &&
    left.size === right.size &&
    left.lastModified === right.lastModified
  );
}
