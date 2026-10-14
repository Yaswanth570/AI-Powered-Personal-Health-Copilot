import { FileText, Upload, X } from "lucide-react";
import { useId, useRef, useState, type DragEvent, type FormEvent } from "react";
import {
  ACCEPTED_FILE_INPUT,
  formatFileSize,
  isSameFile,
  validateFile,
} from "../../lib/fileValidation";
import { isUploadDocumentType, UPLOAD_DOCUMENT_TYPES } from "../../lib/records";
import { cn } from "../../lib/utils";
import type { UploadDocumentType } from "../../types";
import { Button } from "../ui/button";
import { Dialog } from "../ui/dialog";
import { Select } from "../ui/select";

interface PendingFile {
  key: string;
  file: File;
  documentType: UploadDocumentType;
}

export interface SelectedUpload {
  file: File;
  documentType: UploadDocumentType;
}

interface UploadRecordDialogProps {
  open: boolean;
  onClose: () => void;
  onAddDocuments: (uploads: SelectedUpload[]) => void;
}

function pendingKey(file: File): string {
  return `${file.name}-${file.size}-${file.lastModified}`;
}

export function UploadRecordDialog({
  open,
  onClose,
  onAddDocuments,
}: UploadRecordDialogProps) {
  const inputId = useId();
  const errorId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<PendingFile[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  function resetForm() {
    setPending([]);
    setErrors([]);
    setIsDragging(false);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  function ingestFiles(fileList: FileList | File[]) {
    const incoming = Array.from(fileList);
    const nextErrors: string[] = [];
    const accepted: PendingFile[] = [];

    for (const file of incoming) {
      const result = validateFile(file);
      if (!result.ok) {
        nextErrors.push(result.message);
        continue;
      }

      const alreadyListed =
        pending.some((item) => isSameFile(item.file, file)) ||
        accepted.some((item) => isSameFile(item.file, file));
      if (alreadyListed) {
        nextErrors.push(`“${file.name}” is already in the selected list.`);
        continue;
      }

      accepted.push({
        key: pendingKey(file),
        file,
        documentType: "Lab report",
      });
    }

    setErrors(nextErrors);
    if (accepted.length > 0) {
      setPending((current) => [...current, ...accepted]);
    }
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    ingestFiles(event.dataTransfer.files);
  }

  function removeFile(key: string) {
    setPending((current) => current.filter((item) => item.key !== key));
  }

  function updateDocumentType(key: string, value: string) {
    if (!isUploadDocumentType(value)) {
      return;
    }
    setPending((current) =>
      current.map((item) => (item.key === key ? { ...item, documentType: value } : item)),
    );
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.length === 0) {
      return;
    }
    onAddDocuments(pending.map(({ file, documentType }) => ({ file, documentType })));
    resetForm();
    onClose();
  }

  return (
    <Dialog
      open={open}
      className="w-[min(40rem,calc(100%-2rem))]"
      title="Add medical documents"
      description="Choose PDF, JPG, JPEG, or PNG files up to 10 MB each. Files stay in this browser tab only and are not analyzed yet."
      onClose={handleClose}
    >
      <form onSubmit={handleSubmit}>
        <div
          className={cn(
            "rounded-lg border border-dashed px-4 py-8 text-center transition-colors",
            isDragging ? "border-primary bg-accent" : "border-border bg-muted/60",
          )}
          onDragEnter={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            const related = event.relatedTarget;
            if (related instanceof Node && event.currentTarget.contains(related)) {
              return;
            }
            setIsDragging(false);
          }}
          onDrop={handleDrop}
        >
          <Upload className="mx-auto h-6 w-6 text-primary" aria-hidden="true" />
          <p className="mt-3 text-sm font-medium text-foreground">
            Drag and drop files here, or browse
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Multiple PDF, JPG, JPEG, and PNG files. Empty files and files over 10 MB are rejected.
          </p>
          <input
            ref={inputRef}
            id={inputId}
            type="file"
            className="sr-only"
            accept={ACCEPTED_FILE_INPUT}
            multiple
            onChange={(event) => {
              if (event.target.files) {
                ingestFiles(event.target.files);
              }
            }}
          />
          <Button
            type="button"
            variant="secondary"
            className="mt-4"
            onClick={() => inputRef.current?.click()}
          >
            Browse files
          </Button>
        </div>

        {errors.length > 0 ? (
          <ul
            id={errorId}
            className="mt-4 space-y-2 rounded-md border border-warning-border bg-warning-bg px-3 py-3 text-sm text-warning"
            aria-live="polite"
          >
            {errors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        ) : null}

        {pending.length > 0 ? (
          <ul className="mt-4 divide-y divide-border rounded-md border border-border">
            {pending.map((item) => (
              <li
                key={item.key}
                className="flex flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center"
              >
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <FileText className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">{item.file.name}</p>
                    <p className="text-xs text-muted-foreground">{formatFileSize(item.file.size)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 sm:w-56">
                  <label className="sr-only" htmlFor={`type-${item.key}`}>
                    Document type for {item.file.name}
                  </label>
                  <Select
                    id={`type-${item.key}`}
                    value={item.documentType}
                    onChange={(event) => updateDocumentType(item.key, event.target.value)}
                  >
                    {UPLOAD_DOCUMENT_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </Select>
                  <Button
                    type="button"
                    variant="ghost"
                    className="h-10 w-10 shrink-0 p-0"
                    aria-label={`Remove ${item.file.name}`}
                    onClick={() => removeFile(item.key)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-4 text-sm text-muted-foreground">No files selected yet.</p>
        )}

        <div className="mt-5 flex flex-col-reverse justify-end gap-2 sm:flex-row">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={pending.length === 0}>
            Add Documents
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
