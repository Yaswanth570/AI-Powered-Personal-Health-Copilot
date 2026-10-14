/** Client for the document-intelligence backend.

Two endpoints are used in this milestone:
- ``extract-text``: fast selectable-text extraction for PDFs with a text layer.
- ``extract-text-ocr``: OCR for images and scanned PDFs (with selectable-text
  fallback for PDFs that already have a text layer).

The API base URL is read from ``VITE_API_BASE_URL`` (or falls back to the
local FastAPI default). No file contents are logged.
*/

import type {
  AnalyzeDocumentError,
  ExtractedPage,
  MedicalDocumentExtraction,
  OcrExtractionResult,
  PdfExtractionError,
  PdfExtractionResult,
} from "../types";

const DEFAULT_BASE_URL = "http://localhost:8000";

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL as string | undefined;
  return configured?.trim() || DEFAULT_BASE_URL;
}

export class PdfExtractionApiError extends Error {
  public readonly status: number;
  public readonly details: PdfExtractionError | null;

  constructor(message: string, status: number, details: PdfExtractionError | null) {
    super(message);
    this.name = "PdfExtractionApiError";
    this.status = status;
    this.details = details;
  }
}

export class AiAnalysisApiError extends Error {
  public readonly status: number;
  public readonly details: AnalyzeDocumentError | null;

  constructor(message: string, status: number, details: AnalyzeDocumentError | null) {
    super(message);
    this.name = "AiAnalysisApiError";
    this.status = status;
    this.details = details;
  }
}

async function parseErrorResponse(response: Response): Promise<PdfExtractionError | null> {
  try {
    return (await response.json()) as PdfExtractionError;
  } catch {
    return null;
  }
}

async function parseAiErrorResponse(response: Response): Promise<AnalyzeDocumentError | null> {
  try {
    return (await response.json()) as AnalyzeDocumentError;
  } catch {
    return null;
  }
}

/** Send a single PDF to the backend for selectable-text extraction.
 *
 * The file is uploaded as multipart form data. Only the user-initiated
 * "Extract PDF Text" action should call this function.
 */
export async function extractPdfText(file: File): Promise<PdfExtractionResult> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  const response = await fetch(`${getApiBaseUrl()}/api/documents/extract-text`, {
    method: "POST",
    body: formData,
  });

  if (response.ok) {
    return (await response.json()) as PdfExtractionResult;
  }

  const details = await parseErrorResponse(response);
  const message =
    details?.message ||
    `Extraction request failed (HTTP ${response.status} ${response.statusText}).`;

  throw new PdfExtractionApiError(message, response.status, details);
}

/** Send an image or PDF to the backend for OCR text extraction.
 *
 * For PDFs with a selectable text layer, the backend returns that text directly
 * without OCR. For scanned PDFs and images, Tesseract OCR is used. Only the
 * user-initiated "Extract Text with OCR" action should call this function.
 */
export async function extractTextWithOcr(file: File): Promise<OcrExtractionResult> {
  const formData = new FormData();
  formData.append("file", file, file.name);

  const response = await fetch(`${getApiBaseUrl()}/api/documents/extract-text-ocr`, {
    method: "POST",
    body: formData,
  });

  if (response.ok) {
    return (await response.json()) as OcrExtractionResult;
  }

  const details = await parseErrorResponse(response);
  const message =
    details?.message ||
    `OCR request failed (HTTP ${response.status} ${response.statusText}).`;

  throw new PdfExtractionApiError(message, response.status, details);
}

/** Send extracted document text and pages to Gemini AI for structured clinical extraction.
 *
 * Uses the /api/documents/analyze-ai endpoint.
 */
export async function analyzeDocumentWithAi(
  text: string,
  pages?: ExtractedPage[],
  documentTypeHint?: string,
): Promise<MedicalDocumentExtraction> {
  const response = await fetch(`${getApiBaseUrl()}/api/documents/analyze-ai`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      pages,
      document_type_hint: documentTypeHint,
    }),
  });

  if (response.ok) {
    return (await response.json()) as MedicalDocumentExtraction;
  }

  const details = await parseAiErrorResponse(response);
  const message =
    details?.message ||
    `AI analysis request failed (HTTP ${response.status} ${response.statusText}).`;

  throw new AiAnalysisApiError(message, response.status, details);
}
