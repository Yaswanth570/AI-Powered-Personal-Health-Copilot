"""Gemini AI Medical Document Extraction Service.

Uses the official Google Gen AI Python SDK (google-genai) to extract structured,
validated clinical entities from document text with Pydantic validation.

Guardrails enforced:
- Strict fidelity to source text: zero hallucination or extrapolation.
- Distinguishes "not mentioned" from "not detected".
- Never infers diagnoses from laboratory results.
- Preserves exact medication names, doses, frequencies, and durations.
- Extracts evidence quotes and page numbers where available.
- Tracks missing fields and uncertainty flags.
- Safe logging: never logs API keys or raw medical document contents.
- No medical advice or treatment recommendations.
"""

from __future__ import annotations

import json
import logging
from typing import Sequence

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from ..config import Settings, get_settings
from ..schemas import MedicalDocumentExtraction, PageText

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are an expert clinical medical document information extraction system.
Your task is to extract factual, structured medical data from clinical document text with strict fidelity to the source.

STRICT MEDICAL EXTRACTION RULES:
1. FIDELITY & ZERO HALLUCINATION:
   - Extract ONLY information explicitly present in the source text.
   - NEVER invent or assume patient names, dates, diagnoses, medicines, dosages, units, or reference intervals.
   - If an attribute (such as dosage duration or reference range) is not written, leave it null.

2. PATIENT NAME:
   - Extract patient_name ONLY if explicitly written (e.g. "Patient: Smt. Sunita Rao", "Name: Rajesh Kumar").
   - If not explicitly mentioned, return null and add "patient_name not mentioned" to missing_fields.

3. REPORT DATE:
   - Extract report_date ONLY if explicitly stated in the source text. Otherwise return null.

4. DIAGNOSES (CRITICAL SAFETY RULE):
   - Record ONLY diagnoses, clinical impressions, or assessments explicitly written by a physician/report author (e.g. "Diagnosis: Essential Hypertension", "Impression: Acute Bronchitis").
   - NEVER INFER A DIAGNOSIS FROM LAB RESULTS. For example, if Fasting Blood Sugar is 180 mg/dL or HbA1c is 8.5%, DO NOT add "Diabetes Mellitus" as a diagnosis unless a diagnosis statement explicitly says so.
   - If no explicit diagnoses are written, leave diagnoses as an empty list [].

5. MEDICATIONS / PRESCRIPTIONS:
   - Extract each prescribed or documented medication with exact name as written (e.g., "Tab. Metformin HCl", "Cap. Amoxicillin").
   - Extract dose, frequency (e.g. "1-0-1", "OD", "BD", "twice daily"), duration ("5 days", "1 month"), route ("oral", "topical"), and instructions ("after food", "bedtime") only when written.
   - Provide an evidence snippet (the exact quote from the document text) and page_number if known.

6. LAB TESTS & DIAGNOSTIC VALUES:
   - Extract each test name, measured value, unit, reference range, and abnormal flag.
   - DISTINGUISH "NOT MENTIONED" FROM "NOT DETECTED": If a pathogen or marker test was performed and reported negative/undetected (e.g. "HBsAg: Non-reactive" or "COVID-19: Not detected"), record value as "Not detected" or "Non-reactive", and abnormal_flag as false. Do NOT confuse this with an unmentioned test.
   - Set abnormal_flag to true ONLY if explicitly flagged in the source (e.g., marked "High", "Low", "*", "Abnormal") or clearly outside stated reference range. Otherwise false or null.

7. MISSING FIELDS:
   - List standard clinical fields expected for this type of record that were NOT mentioned in the text (e.g., "patient_name not mentioned", "report_date not mentioned", "duration not specified for Metformin").

8. UNCERTAINTIES & OCR ARTIFACTS:
   - List any ambiguities, illegible words, OCR errors, or unclear handwriting that may affect interpretation.

9. CONFIDENCE & SUMMARY:
   - Assign confidence ("high", "medium", or "low") with a brief confidence_reason explaining text clarity.
   - Provide a neutral, objective summary of the document without clinical recommendations.
   - DO NOT provide medical advice, diagnosis, triage, or treatment recommendations.
"""


class GeminiExtractionError(Exception):
    """Base exception for Gemini document extraction failures."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class GeminiConfigError(GeminiExtractionError):
    """Raised when the Gemini API key is missing or invalid."""

    def __init__(self, message: str = "Gemini API key is not configured.") -> None:
        super().__init__(code="api_key_missing", message=message)


class GeminiInputError(GeminiExtractionError):
    """Raised when input text is invalid (empty or oversized)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message)


class GeminiRateLimitError(GeminiExtractionError):
    """Raised when Gemini API rate limits or quotas are hit."""

    def __init__(
        self,
        message: str = "Gemini API rate limit exceeded. Please wait a moment and try again.",
    ) -> None:
        super().__init__(code="rate_limit_exceeded", message=message)


class GeminiInvalidOutputError(GeminiExtractionError):
    """Raised when model output fails JSON or Pydantic validation."""

    def __init__(
        self,
        message: str = "Model output could not be validated against the clinical schema.",
    ) -> None:
        super().__init__(code="invalid_output", message=message)


class GeminiApiError(GeminiExtractionError):
    """Raised when the Gemini API returns an error or is unreachable."""

    def __init__(
        self,
        message: str = "Gemini API error occurred during document extraction.",
    ) -> None:
        super().__init__(code="api_error", message=message)


import re

FALLBACK_MODELS = ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")


def _clean_api_error_message(raw_msg: str) -> str:
    """Sanitize Google API error messages, removing secrets while keeping diagnostic details."""
    if not raw_msg:
        return ""
    # Strip potential key parameters or tokens
    cleaned = re.sub(r"key=[A-Za-z0-9_-]+", "key=[REDACTED]", raw_msg)
    cleaned = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED]", cleaned)
    # If the message is a stringified JSON dict e.g. {'error': {'message': '...'}}
    if "'message':" in cleaned or '"message":' in cleaned:
        match = re.search(r"['\"]message['\"]\s*:\s*['\"]([^'\"]+)['\"]", cleaned)
        if match:
            cleaned = match.group(1)
    return " ".join(cleaned.split()).strip()


def _build_user_prompt(
    text: str,
    pages: Sequence[PageText] | None = None,
    document_type_hint: str | None = None,
) -> str:
    """Build the structured user prompt containing page-delimited text."""
    parts: list[str] = []

    if document_type_hint:
        parts.append(f"Document Type Hint: {document_type_hint.strip()}")

    parts.append("--- BEGIN EXTRACTED MEDICAL DOCUMENT TEXT ---")

    if pages and len(pages) > 0:
        for page in pages:
            parts.append(f"=== PAGE {page.page_number} ===")
            parts.append(page.text if page.text.strip() else "(no text on this page)")
    else:
        parts.append(text)

    parts.append("--- END EXTRACTED MEDICAL DOCUMENT TEXT ---")
    parts.append(
        "Please extract all factual clinical entities according to the system instructions "
        "and return a valid JSON object matching the requested schema."
    )
    return "\n\n".join(parts)


def get_gemini_client(api_key: str | None = None) -> genai.Client:
    """Create a Google Gen AI client with the configured API key."""
    settings = get_settings()
    key = api_key or settings.gemini_api_key
    if not key:
        raise GeminiConfigError(
            "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env."
        )
    return genai.Client(api_key=key)


def extract_medical_document(
    text: str,
    pages: Sequence[PageText] | None = None,
    document_type_hint: str | None = None,
    settings: Settings | None = None,
    client: genai.Client | None = None,
) -> MedicalDocumentExtraction:
    """Extract validated structured medical data from document text using Gemini.

    Parameters
    ----------
    text:
        Raw extracted text from selectable PDF layer or OCR.
    pages:
        Optional sequence of PageText objects providing page-by-page text.
    document_type_hint:
        Optional hint (e.g. 'Lab report', 'Prescription').
    settings:
        Optional Settings override.
    client:
        Optional pre-configured genai.Client (useful for testing and dependency injection).

    Returns
    -------
    MedicalDocumentExtraction:
        Validated Pydantic model containing structured extraction.
    """
    cfg = settings or get_settings()

    # 1. Validate input text.
    cleaned_text = text.strip()
    if not cleaned_text:
        raise GeminiInputError(
            code="empty_text",
            message="Document text is empty or contains no extractable content.",
        )

    if len(cleaned_text) > cfg.max_ai_text_chars:
        raise GeminiInputError(
            code="text_too_large",
            message=(
                f"Document text length ({len(cleaned_text):,} chars) exceeds the allowed limit "
                f"of {cfg.max_ai_text_chars:,} characters."
            ),
        )

    # 2. Initialize Gemini client if not provided.
    if client is None:
        client = get_gemini_client(cfg.gemini_api_key)

    # 3. Build prompt and configuration.
    user_prompt = _build_user_prompt(
        text=cleaned_text,
        pages=pages,
        document_type_hint=document_type_hint,
    )

    model_name = cfg.gemini_model or "gemini-3.1-flash-lite"
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=MedicalDocumentExtraction,
        temperature=0.0,
        system_instruction=SYSTEM_INSTRUCTION,
    )

    # Candidate models: start with configured model, then append stable fallbacks.
    models_to_try = [model_name]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    response = None
    used_model = model_name

    # 4. Invoke Gemini model safely with fallback if model is sunset/unavailable.
    for idx, current_model in enumerate(models_to_try):
        logger.info(
            "Calling Gemini model %s for structured extraction (len: %d chars)",
            current_model,
            len(cleaned_text),
        )
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=user_prompt,
                config=config,
            )
            used_model = current_model
            if idx > 0:
                logger.info(
                    "Primary model '%s' was unavailable; fallback to '%s' succeeded.",
                    model_name,
                    current_model,
                )
            break
        except errors.APIError as exc:
            code = getattr(exc, "code", 500)
            message = str(getattr(exc, "message", None) or exc or "")
            clean_diag = _clean_api_error_message(message)
            logger.warning(
                "Gemini API error for model %s: HTTP %s (%s)",
                current_model,
                code,
                clean_diag,
            )

            # Auth errors are not model-specific: reject immediately.
            if code in (401, 403) or "API_KEY_INVALID" in message:
                raise GeminiConfigError(
                    "Invalid Gemini API key provided. Check GEMINI_API_KEY in backend/.env."
                ) from exc

            # Quota/rate-limit errors are not model-specific: reject immediately.
            if code == 429 or "RESOURCE_EXHAUSTED" in message or "429" in str(code):
                raise GeminiRateLimitError(
                    "Gemini API rate limit or quota exceeded. Please try again shortly."
                ) from exc

            # If model is sunset / not found (404) or experiencing spikes (503), try next fallback
            is_recoverable_status = code in (404, 503) or "NOT_FOUND" in message or "UNAVAILABLE" in message
            if is_recoverable_status and idx < len(models_to_try) - 1:
                logger.warning(
                    "Model %s returned HTTP %s (%s). Attempting fallback to %s.",
                    current_model,
                    code,
                    clean_diag,
                    models_to_try[idx + 1],
                )
                continue

            # Return actionable error without leaking secrets or text
            if code == 404 or "NOT_FOUND" in message:
                detail = clean_diag or "Model is no longer available or was not found."
                raise GeminiApiError(
                    f"Gemini API request failed (HTTP 404): Model '{current_model}' is unavailable. {detail} "
                    "Please update GEMINI_MODEL in backend/.env to a supported model (e.g. gemini-3.1-flash-lite)."
                ) from exc
            if code == 503 or "UNAVAILABLE" in message:
                detail = clean_diag or "Model is currently experiencing high demand."
                raise GeminiApiError(
                    f"Gemini API request failed (HTTP 503): {detail} "
                    "Please retry in a moment or change GEMINI_MODEL in backend/.env."
                ) from exc

            raise GeminiApiError(
                f"Gemini API request failed (HTTP {code})" + (f": {clean_diag}" if clean_diag else ".")
            ) from exc
        except Exception as exc:
            logger.warning("Unexpected error communicating with Gemini API: %s", type(exc).__name__)
            if idx < len(models_to_try) - 1:
                continue
            raise GeminiApiError("Could not connect to Gemini service. Please check network connectivity.") from exc

    if response is None:
        raise GeminiApiError("Failed to receive a valid response from Gemini service.")

    # 5. Validate model response text.
    raw_response_text = getattr(response, "text", None)
    if not raw_response_text or not raw_response_text.strip():
        logger.warning("Gemini returned empty response text.")
        raise GeminiInvalidOutputError("Gemini returned an empty response.")

    try:
        extraction = MedicalDocumentExtraction.model_validate_json(raw_response_text)
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.warning("Failed to validate Gemini response against schema: %s", type(exc).__name__)
        raise GeminiInvalidOutputError(
            "Model response could not be validated against the medical schema."
        ) from exc

    # 6. Ensure model_used and disclaimer are set consistently.
    extraction.model_used = used_model
    return extraction
