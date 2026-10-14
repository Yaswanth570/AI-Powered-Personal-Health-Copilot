# Personal Health Copilot

Frontend foundation and first stage of document intelligence for the Altrix Labs **AI-Powered Personal Health Copilot** challenge at byteXL HacXLerate 2026.

The product vision is a calm workspace where people can keep medical files, understand laboratory results in plain language, organize prescriptions, and review a health timeline.

## Current scope

This repository implements **Steps 1–9**:

1. A typed React + TypeScript + Vite dashboard with synthetic Indian demo content and a client-side medical document upload workflow.
2. **PDF text extraction** via a Python FastAPI backend using PyMuPDF for PDFs that already contain a selectable text layer.
3. **OCR text extraction** using Tesseract for scanned PDFs and image documents (JPG/JPEG/PNG).
4. **Interactive review flow** with side-by-side or tabbed verification against original extracted text.
5. **Gemini AI medical document extraction** using Google Gen AI (`gemini-3.1-flash-lite`, fallback cascade to `3.5-flash-lite` and `3.8-flash`) for structured clinical entities (diagnoses, medicines with exact doses, lab test results with reference ranges and abnormal flags, missing fields, uncertainties, and evidence snippets) with strict Pydantic validation and clinical safety guardrails.
6. **PostgreSQL Persistence** with SQLAlchemy 2.x, psycopg 3 driver, and Alembic migrations:
   - Normalized clinical schema: `patients`, `medical_documents`, `diagnoses`, `medications`, `lab_results`.
   - Transactional atomic document + extraction persistence endpoint (`POST /api/documents/save`).
   - Foreign keys, cascade deletions, indexes, and full CRUD operations.
   - React frontend integration for loading saved records, confirming saves, editing metadata, and safe deletion.
   - Development SQLite fallback (`sqlite:///./health_copilot.db`) when local PostgreSQL is not configured.
7. **Telugu Health Summaries & FHIR Interoperability (Step 7)**:
   - **Telugu Health Explanations**: English/Telugu language toggle in the AI analysis view (English default). Generates clear, patient-friendly Telugu explanations for diagnoses, prescribed medicines, and laboratory findings using Gemini. Preserves exact English medicine names, dosages, units, and dates accurately. Distinct source facts vs explanations, zero hallucination, and dual-language clinical safety disclaimer.
   - **HL7 FHIR R4 Interoperability**: Validated FHIR-inspired export of persisted patient and document records into HL7 FHIR Release 4 Collection Bundles. Standard resource mappings (`Patient`, `DocumentReference`, `Condition`, `MedicationStatement`, `Observation`) with consistent UUID references (`urn:uuid:{id}`) and cross-references.
   - **FHIR Preview & Download UI**: Interactive modal with resource breakdown metrics, formatted JSON inspector, copy button, and `.json` file download.
8. **Final Integration Audit & Hardening (Step 8)**:
   - End-to-end audit across PDF extraction, OCR, Gemini clinical extraction, database persistence, Telugu summaries, and FHIR export.
9. **Persistent Personal Health AI Copilot (Step 9)**:
   - **Health AI Interface**: Dedicated sidebar page matching the calm teal-and-white theme, conversational chat, suggested prompt chips, expandable evidence citations, and persistent consultation history.
   - **Persistent Medical Memory**: Patient-scoped queries retrieve saved diagnoses, medications, and chronologically ordered lab investigations. Distinguishes verified clinical facts from chat context.
   - **Grounded Personalized AI**: Gemini SDK integration with structured citations linking every answer to source documents, encounter dates, and lab values. Strict prompt injection defense and clinical guardrails (no prescriptions or dose alterations, emergency symptom warnings).
   - **Patient Isolation & Security**: Backend validates patient ownership on all conversations and queries. Zero cross-patient leakage.

Included:

- React + TypeScript (strict) + Vite, Tailwind CSS, shadcn-compatible UI primitives
- Responsive dashboard shell, overview cards, sample records table, lab and timeline previews
- Client-side search over demo, session, and database records
- Upload dialog (drag-and-drop, browse, multi-select, 10 MB limit, PDF/JPG/JPEG/PNG, validation)
- PostgreSQL persistence with automatic SQLite fallback when `DATABASE_URL` is omitted
- **FastAPI backend** (`backend/`) with:
  - `/api/patients` — create, list, and retrieve patient profiles
  - `/api/documents/save` — transactional atomic persistence of documents and normalized clinical entities
  - `/api/documents` & `/api/patients/{id}/documents` — list saved documents with entity counts
  - `/api/documents/{id}` — retrieve full detail, update metadata (PATCH), and cascade delete (DELETE)
  - `/api/documents/extract-text` — extracts selectable text from a PDF page-by-page using PyMuPDF
  - `/api/documents/extract-text-ocr` — OCR for JPG/JPEG/PNG images and scanned PDFs (Tesseract)
  - `/api/documents/analyze-ai` — Gemini AI structured medical extraction with strict schema validation
  - `/api/documents/explain-telugu` & `/api/documents/{id}/explain-telugu` — Patient-friendly Telugu health summary and explanations
  - `/api/patients/{id}/fhir` & `/api/documents/{id}/fhir` — Validated HL7 FHIR R4 Bundle JSON export
  - `/api/patients/{id}/conversations` (GET, POST) — list and create conversational chat sessions
  - `/api/patients/{id}/conversations/{conv_id}` (GET, DELETE) — get ordered message history and delete session
  - `/api/patients/{id}/conversations/{conv_id}/messages` (POST) — send grounded query with evidence citations
  - `/api/patients/{id}/chat` (POST) — convenience endpoint for auto-created consultation sessions
- **Frontend actions**: "Health AI" consultation page, "Analyze with AI", "English / తెలుగు" language selector, "Export Patient FHIR Bundle", "FHIR R4 Export", "Save to Health Records", "Edit Metadata", and "Delete Record".

Not included (future milestones):

- User authentication & multi-tenant access control
- Multilingual voice synthesis (text-to-speech)
- Medical diagnosis or clinical treatment generation (strictly forbidden)


All numbers, names, and laboratory values on screen are labelled synthetic demo content. They are not real patient data and are not medical advice.

## Architecture

```
┌─────────────────────────┐         ┌────────────────────────────────────────────────────────┐
│  Frontend (Vite/React)  │ ──────▶ │  Backend (FastAPI + PyMuPDF + Tesseract + Google GenAI)│
│  http://localhost:5173  │  HTTP   │  http://localhost:8000                                 │
│                         │         │                                                        │
│  - Upload dialog        │         │  - /health                                             │
│  - Records list         │         │  - /api/documents/extract-text                         │
│  - Analyze with AI      │         │    (PDF text layer → text)                             │
│  - Extract PDF Text     │         │  - /api/documents/extract-text-ocr                     │
│  - Extract Text w/ OCR  │         │    (image/scanned-PDF → OCR → text)                   │
│  - Structured AI review │         │  - /api/documents/analyze-ai                           │
│  - Raw text review      │         │    (extracted text → Gemini 2.5 Flash → validated JSON)│
└─────────────────────────┘         └────────────────────────────────────────────────────────┘
```

- The frontend never sends a file automatically. A file is sent to the backend **only when the user clicks an action** (e.g. "Analyze with AI" or "PDF Text").
- Uploaded files are processed **in memory** by the backend and never written to disk.
- Document contents and API keys are **never logged**.
- For PDFs, the OCR endpoint first tries the fast selectable-text path; OCR is only used when no text layer exists.
- The AI endpoint reuses the raw text obtained from PDF extraction or OCR; it does not implement a redundant extraction pipeline.
- Structured output is enforced via Pydantic response models and `temperature=0.0`.

## Run locally

### Prerequisites

- Node.js 20 or later (frontend)
- Python 3.11 or later (backend; tested on 3.14)
- **Tesseract OCR** (required for image and scanned-PDF text recognition)

#### Installing Tesseract

**Windows** (recommended: UB-Mannheim build via winget):

```powershell
winget install --id UB-Mannheim.TesseractOCR
```

This installs Tesseract to `C:\Program Files\Tesseract-OCR\` and includes the
`eng` (English) language data by default. The backend auto-discovers this
location, so adding it to `PATH` is optional but recommended.

Verify the install and list available languages:

```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs
```

**macOS:** `brew install tesseract`
**Linux (Debian/Ubuntu):** `sudo apt install tesseract-ocr`

To add more languages (e.g. for multilingual documents), install the
corresponding `tesseract-ocr-<lang>` package or download `.traineddata` files
into the `tessdata` directory.

> If Tesseract is not installed, the OCR endpoint returns HTTP 503 with a
> setup message instead of crashing. The selectable-text PDF endpoint
> (`/extract-text`) continues to work without Tesseract.

### 1. Frontend

```bash
npm install
cp .env.example .env        # optional; sets VITE_API_BASE_URL
npm run dev
```

Open the URL printed by Vite (typically `http://localhost:5173`).

#### Frontend environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the document-intelligence backend. |

`.env` and `.env.*` (except `.env.example`) are gitignored so API configuration stays local.

### 2. Backend & PostgreSQL Setup

#### Step A: PostgreSQL Installation & Database Creation

**Option 1: Windows Local PostgreSQL**
1. Download and install PostgreSQL (version 15, 16, or 17) from [postgresql.org](https://www.postgresql.org/download/windows/) or via winget:
   ```powershell
   winget install PostgreSQL.PostgreSQL
   ```
2. Start the PostgreSQL service (if not running automatically):
   ```powershell
   net start postgresql-x64-16
   ```
3. Open `psql` or pgAdmin and create the development database:
   ```sql
   CREATE DATABASE health_copilot;
   ```

**Option 2: Docker**
```bash
docker run --name health-copilot-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=health_copilot -p 5432:5432 -d postgres:16
```

**Option 3: Seamless Local SQLite Development Fallback**
If PostgreSQL is not installed or accessible on your machine, the backend automatically defaults to a local SQLite database (`sqlite:///./health_copilot.db`). No configuration or external service is required to get started immediately.

#### Step B: Backend Configuration & Migrations

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env
```

Configure `DATABASE_URL` in `backend/.env`:
```ini
# PostgreSQL with psycopg 3 driver
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/health_copilot

# Or omit DATABASE_URL / leave empty to use the local SQLite fallback
# DATABASE_URL=sqlite:///./health_copilot.db
```

Run Alembic database migrations:
```bash
python -m alembic upgrade head
```

Start the FastAPI backend:
```bash
python -m uvicorn app.main:app --reload
```

The backend runs at `http://localhost:8000`. Interactive Swagger API docs are available at `http://localhost:8000/docs`.

#### Backend environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `None` (falls back to SQLite `health_copilot.db`) | PostgreSQL connection string (`postgresql+psycopg://user:password@host:port/dbname`). Kept strictly in `backend/.env`. |
| `MAX_UPLOAD_BYTES` | `10485760` (10 MB) | Maximum allowed upload size in bytes. |
| `CORS_ORIGINS` | Vite dev ports 5173–5175 | Comma-separated list of allowed CORS origins. |
| `OCR_MAX_PAGES` | `20` | Maximum PDF pages that OCR will process. |
| `OCR_DPI` | `200` | Resolution (DPI) used when rendering PDF pages for OCR. Capped at 400. |
| `OCR_LANGUAGES` | `eng` | Comma-separated Tesseract language codes to use. |
| `GEMINI_API_KEY` | `None` | Google Gen AI API key (from Google AI Studio). Kept strictly on backend. |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Gemini model used for clinical structured extraction (supports gemini-3.1-flash-lite, gemini-3.5-flash-lite, gemini-3.8-flash). |
| `MAX_AI_TEXT_CHARS` | `150000` | Maximum character length of input document text accepted for AI extraction. |

## Persistence endpoints (Step 6)

All database operations execute within atomic transactions with immediate rollback on error.

### Patient endpoints
- `POST /api/patients` — Create a new patient profile (`display_name`, `age`, `gender`).
- `GET /api/patients` — List all patient profiles with document counts.
- `GET /api/patients/{patient_id}` — Get single patient profile by ID.
- `GET /api/patients/{patient_id}/documents` — List all saved documents for a patient.

### Document persistence endpoints
- `POST /api/documents/save` — Atomically persist a medical document and its normalized clinical findings (diagnoses, medications, lab results) in a single database transaction. Returns full saved detail.
- `GET /api/documents` — List saved documents with structured entity counts (optional `?patient_id=` query filter).
- `GET /api/documents/{document_id}` — Retrieve full document detail, including raw text, AI extraction JSON snapshot, and relational diagnoses, medications, and lab results.
- `PATCH /api/documents/{document_id}` — Update document metadata (filename, document type, summary).
- `DELETE /api/documents/{document_id}` — Safely cascade-delete a document and all its linked clinical records without altering other patient data.

## PDF text extraction endpoint

`POST /api/documents/extract-text`

- Accepts a single PDF file as multipart form data (field name `file`).
- Enforces the 10 MB size limit (configurable).
- Extracts text page-by-page with PyMuPDF.
- Returns JSON:

```json
{
  "page_count": 2,
  "pages": [
    { "page_number": 1, "text": "...", "char_count": 1234 },
    { "page_number": 2, "text": "...", "char_count": 567 }
  ],
  "full_text": "...",
  "total_char_count": 1801,
  "has_selectable_text": true,
  "note": "Text was extracted from selectable PDF content. No OCR was performed."
}
```

Error responses use HTTP 4xx with a consistent shape:

```json
{ "error": "invalid_pdf", "message": "The file is not a valid PDF and could not be opened." }
```

| Error code | Meaning |
| --- | --- |
| `file_too_large` | Upload exceeds the 10 MB limit |
| `unsupported_file_type` | File is not a supported type (`.pdf`, `.jpg`, `.jpeg`, `.png`) |
| `invalid_pdf` | File could not be opened as a PDF |
| `encrypted_pdf` | PDF is password-protected |
| `empty_document` | File is empty or has no pages |
| `no_text_extracted` | (Reserved) PDF has no text layer |
| `ocr_unavailable` | Tesseract is not installed or a requested language is missing |
| `too_many_pages` | PDF exceeds the OCR page-count limit |

When a PDF has no selectable text, the `/extract-text` endpoint returns HTTP 200 with `has_selectable_text: false` and a `note` suggesting OCR. **No fabricated or synthetic text is ever returned.**

## OCR text extraction endpoint

`POST /api/documents/extract-text-ocr`

- Accepts a single PDF, JPG, JPEG, or PNG file as multipart form data (field name `file`).
- Enforces the 10 MB size limit (configurable).
- Validates file content by magic bytes (not just the filename extension).
- For **PDFs**: first extracts the selectable text layer. If a text layer exists, it is returned directly (no OCR). If not, each page is rendered to an image and OCR'd with Tesseract.
- For **images** (JPG/JPEG/PNG): OCR is applied directly.
- OCR is capped at `OCR_MAX_PAGES` (default 20) pages and rendered at `OCR_DPI` (default 200, max 400) to limit resource usage.
- Returns JSON:

```json
{
  "page_count": 1,
  "pages": [
    { "page_number": 1, "text": "...", "char_count": 123, "method": "ocr" }
  ],
  "full_text": "...",
  "total_char_count": 123,
  "has_text": true,
  "ocr_engine": "tesseract",
  "ocr_languages": ["eng"],
  "note": "Text was recognized from the image with Tesseract OCR..."
}
```

Each page includes a `method` field of `"selectable"` (PDF text layer) or `"ocr"`.
When no text is recognized, `has_text` is `false` and the `note` explains that no
text was detected — **no text is fabricated**.

### OCR quality and safety notes

- OCR output is **raw** and may contain errors. It is presented for human review only.
- Tesseract may perform poorly on **handwritten text** (e.g. handwritten prescriptions). Do not assume handwriting is read accurately.
- The system does **not** silently correct medicine names, doses, units, or test values.
- No AI interpretation or medical analysis is performed in this milestone.
- Installed OCR languages are reported in the response (`ocr_languages`).

## Gemini AI medical document extraction endpoint

`POST /api/documents/analyze-ai`

- Accepts extracted document text (from selectable PDF or OCR) and optional page structures.
- Invokes Gemini AI (`gemini-3.1-flash-lite`) via the official Google Gen AI SDK (`google-genai`).
- Enforces strict Pydantic validation on the response schema.
- **Strict Clinical Safety Guardrails**:
  - **Zero hallucination / fidelity**: Only extracts information explicitly written in the source text.
  - **No inferred diagnoses**: Diagnoses are never inferred from lab test values (e.g. high blood sugar does not imply diabetes unless explicitly stated by the clinician).
  - **Prescription accuracy**: Medicines, dosages, frequencies, and durations are captured exactly as written.
  - **Distinguishes negative vs unmentioned**: A non-reactive or negative lab test (e.g. "HBsAg: Not detected") is distinguished from an unperformed test.
  - **Evidence quotes and page numbers**: Tracks source snippets and page indices for user verification.
  - **Missing fields and uncertainties**: Highlights clinical information expected for the document type that was omitted.
  - **Safe logging**: Never logs API keys or raw medical document text.

Example response JSON:

```json
{
  "document_type": "Prescription and Clinical Summary",
  "report_date": "12-Oct-2026",
  "patient_name": "Smt. Kamala Devi",
  "patient_age": "58 Yrs",
  "patient_gender": "Female",
  "diagnoses": [
    {
      "diagnosis": "Type 2 Diabetes Mellitus",
      "status": "Uncontrolled",
      "evidence": "1. Type 2 Diabetes Mellitus (Uncontrolled)",
      "page_number": 1
    }
  ],
  "medicines": [
    {
      "name": "Tab. Metformin HCl",
      "dose": "500 mg",
      "frequency": "1-0-1",
      "duration": "30 days",
      "route": "Oral",
      "instructions": "Take after food",
      "evidence": "Tab. Metformin HCl 500 mg — 1 tablet twice daily (1-0-1)...",
      "page_number": 1
    }
  ],
  "lab_tests": [
    {
      "test_name": "Fasting Blood Sugar (FBS)",
      "value": "142",
      "unit": "mg/dL",
      "reference_range": "70 - 100 mg/dL",
      "abnormal_flag": true,
      "evidence": "Fasting Blood Sugar (FBS): 142 mg/dL [Ref: 70 - 100 mg/dL] (HIGH)",
      "page_number": 1
    }
  ],
  "missing_fields": [],
  "uncertainties": [],
  "confidence": "high",
  "confidence_reason": "High-clarity printed clinical prescription...",
  "summary": "Outpatient consultation summary...",
  "disclaimer": "AI-extracted medical information. Always verify against original clinical documents. Not a medical diagnosis or clinical recommendation.",
  "model_used": "gemini-3.1-flash-lite"
}
```

| Error code | HTTP Status | Meaning |
| --- | --- | --- |
| `api_key_missing` | 503 | `GEMINI_API_KEY` is not configured in `backend/.env` |
| `empty_text` | 400 | Provided document text contains no characters |
| `text_too_large` | 413 | Document text exceeds `MAX_AI_TEXT_CHARS` (150,000 chars) |
| `rate_limit_exceeded` | 429 | Gemini quota or rate limits exceeded |
| `api_error` | 502 | Gemini API returned an upstream service error |
| `invalid_output` | 502 | Model output failed schema validation |

## Useful commands

### Frontend

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Vite development server |
| `npm run build` | Typecheck with `tsc -b`, then create a production build |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | Run oxlint |
| `npx tsc -b --pretty false` | TypeScript typecheck only |

### Backend

### Backend

| Command | Purpose |
| --- | --- |
| `python -m alembic upgrade head` | Apply database migrations to current revision |
| `python -m uvicorn app.main:app --reload` | Start the backend with hot reload |
| `python -m pytest tests/ -v` | Run the full backend test suite (39 tests: PDF, OCR, Gemini, Persistence) |

## Project layout

```
backend/
  alembic/                   # Alembic database migration scripts
    versions/                # Revision migration files
    env.py                   # Migration environment setup (Base.metadata)
  app/
    api/
      routes.py              # PDF extraction, OCR, Gemini AI routes
      persistence_routes.py  # Patients & Medical Documents CRUD routes
    db/
      base.py                # DeclarativeBase definition
      models.py              # Patient, MedicalDocument, DiagnosisRecord, MedicationRecord, LabResultRecord
      session.py             # SQLAlchemy 2.0 Engine, sessionmaker, get_db dependency
      init_db.py             # Schema initialization & Indian demo patient seeding
    services/
      pdf_extractor.py       # PyMuPDF extraction logic (selectable text)
      ocr_service.py         # Tesseract OCR for images and scanned PDFs
      gemini_extractor.py    # Gemini AI structured clinical extraction
      telugu_explainer.py    # Gemini AI Telugu clinical explanation service
      fhir_exporter.py       # HL7 FHIR R4 Bundle mapping and export service
    schemas.py               # Pydantic request/response & persistence models
    config.py                # Environment-driven settings (DATABASE_URL, GEMINI_API_KEY)
    main.py                  # FastAPI app, lifespan, CORS, router mounting
  tests/
    test_pdf_extraction.py   # Selectable-text PDF extraction tests
    test_ocr_extraction.py   # OCR tests (images, scanned PDFs, errors)
    test_ai_extraction.py    # Mocked Gemini AI tests (safety rules, errors)
    test_persistence.py      # PostgreSQL persistence tests (transactions, CRUD, cascades)
    test_telugu_summary.py   # Telugu explanation tests (fidelity, disclaimer, errors)
    test_fhir_export.py      # FHIR R4 Bundle tests (validation, cross-refs, 404s)
  requirements.txt
src/
  components/
    layout/                  # App shell, sidebar, header
    dashboard/               # Overview, records, upload dialog, extraction UI
      AiAnalysisView.tsx     # Structured clinical extraction display, English/Telugu selector
      FhirExportDialog.tsx   # Interactive FHIR R4 preview, JSON copy & download
      RecentRecords.tsx      # Record list with Analyze with AI, PostgreSQL Save & FHIR export
      SavedRelationalView.tsx# Normalized relational clinical tables view
    ui/                      # Reusable button, card, input, badge, dialog
  data/demoData.ts           # Synthetic Indian demo content
  lib/
    fileValidation.ts        # Client-side upload validation
    records.ts               # Session-record creation, summary cards
    pdfApi.ts                # Backend API client for extraction, OCR, and Gemini AI
    persistenceApi.ts        # Backend API client for PostgreSQL persistence & FHIR/Telugu
    utils.ts
  types/                     # TypeScript definitions & Pydantic mirror interfaces
  App.tsx
  main.tsx
  index.css
```

## Current limitations

- OCR uses Tesseract, which works best on **printed text**. It may perform poorly on handwriting, low-resolution scans, or complex layouts. Handwritten prescriptions may not be read accurately.
- AI extraction relies on Gemini model availability and a configured `GEMINI_API_KEY`.
- AI output is structured and validated against source text, but is not a substitute for clinical review. All extracted data must be verified against the physical/digital original document.
- Local PostgreSQL instance or development SQLite fallback required for persistent storage.
- No user authentication, authorization, or multi-tenant access control (planned for future milestone).
- Scanned PDFs are rendered page-by-page for OCR, capped at 20 pages (configurable) to limit resource usage.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| OCR returns HTTP 503 `ocr_unavailable` | Tesseract not installed or not on PATH | Install Tesseract (`winget install UB-Mannheim.TesseractOCR` on Windows) and restart the backend |
| OCR returns 503 mentioning a missing language | A configured `OCR_LANGUAGES` code is not installed | Run `tesseract --list-langs` to see installed languages, or install the missing language data |
| OCR finds no text (`has_text: false`) | Image is blank, low-resolution, or handwritten | Try a higher-resolution scan or a printed document |
| PDF OCR fails with `too_many_pages` | PDF has more than `OCR_MAX_PAGES` pages | Split the PDF or increase `OCR_MAX_PAGES` |

## Hackathon note

Do not treat this interface as a clinical tool. Sample reference ranges are illustrative only. Extracted text is raw document content and must be reviewed by a licensed clinician before any clinical decision.
