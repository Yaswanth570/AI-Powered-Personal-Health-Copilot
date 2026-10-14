"""Gemini AI Telugu Health Summary and Explanation Service.

Generates clear, patient-friendly Telugu explanations of medical documents:
- Explains clinical diagnoses, prescribed medicines, and lab tests in Telugu.
- Preserves original medical terms, medicine names, dosages, units, and numerical values.
- Never invents diagnoses, treatment recommendations, or missing facts.
- Distinguishes factual source document data from educational explanations.
- Employs strict Pydantic schema validation with Google Gen AI SDK.
"""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from ..config import Settings, get_settings
from ..schemas import MedicalDocumentExtraction, TeluguHealthSummary
from .gemini_extractor import (
    FALLBACK_MODELS,
    GeminiApiError,
    GeminiConfigError,
    GeminiInvalidOutputError,
    GeminiRateLimitError,
    _clean_api_error_message,
)

logger = logging.getLogger(__name__)

TELUGU_SYSTEM_INSTRUCTION = """You are an empathetic, culturally fluent clinical medical communicator who translates and explains medical records in clear, patient-friendly Telugu (తెలుగు లిపి).

Your goal is to help a Telugu-speaking patient or family member understand their medical document clearly without confusion or alarm.

STRICT MEDICAL EXPLANATION & TRANSLATION RULES:
1. SCRIPT & LANGUAGE:
   - Write all explanations in natural, clear Telugu script (తెలుగు).
   - Keep language simple, respectful, and easy to understand for everyday Telugu speakers.

2. NUMERICAL & CLINICAL PRESERVATION (CRITICAL):
   - ALWAYS PRESERVE exact numbers, dates, dosages, units, and measurements as written in the source.
   - For example: if a medicine is "Tab. Metformin 500 mg (1-0-1)", DO NOT alter 500 mg or 1-0-1.
   - For lab tests: if Fasting Blood Sugar is "142 mg/dL [Ref: 70 - 100 mg/dL]", preserve 142, mg/dL, and 70 - 100 mg/dL exactly.

3. DUAL-LANGUAGE MEDICAL TERMS:
   - Always retain the English clinical term alongside or in brackets for clarity.
   - Example for diagnosis: "రక్తపోటు (Hypertension / హైపర్‌టెన్షన్)" or "మధుమేహం (Type 2 Diabetes Mellitus)".
   - Example for medicine: "Tab. Metformin HCl 500 mg" — explain what it is commonly used for in Telugu, but keep the brand/generic name identical.

4. FIDELITY & ZERO HALLUCINATION:
   - NEVER invent diagnoses or conditions not documented in the extraction.
   - NEVER give unsolicited treatment advice, dosage modifications, or emergency triage advice.
   - Explain what the test or medicine is, what the documented value means according to the report, and remind the patient to follow their doctor's instructions.

5. SAFETY DISCLAIMER:
   - Always include the patient safety disclaimer in Telugu:
     "ఈ సమాచారం కేవలం రోగి అవగాహన కొరకు మాత్రమే. ఇది వైద్య నిర్ధారణ లేదా చికిత్స సలహా కాదు. ఎల్లప్పుడూ మీ వైద్యుడిని సంప్రదించండి."
"""


def explain_medical_extraction_in_telugu(
    extraction: MedicalDocumentExtraction,
    settings: Settings | None = None,
) -> TeluguHealthSummary:
    """Generate patient-friendly Telugu explanations from a validated clinical extraction."""
    cfg = settings or get_settings()

    api_key = cfg.gemini_api_key
    if not api_key or not api_key.strip():
        raise GeminiConfigError(
            "Gemini API key is not configured. Add GEMINI_API_KEY to backend/.env."
        )

    model_name = cfg.gemini_model or "gemini-3.1-flash-lite"
    client = genai.Client(api_key=api_key.strip())

    # Build prompt from structured extraction
    prompt_payload = {
        "document_type": extraction.document_type,
        "report_date": extraction.report_date,
        "patient_name": extraction.patient_name,
        "diagnoses": [d.model_dump() for d in extraction.diagnoses],
        "medicines": [m.model_dump() for m in extraction.medicines],
        "lab_tests": [l.model_dump() for l in extraction.lab_tests],
        "summary": extraction.summary,
    }

    user_prompt = (
        "Please provide clear, patient-friendly Telugu explanations for the following extracted clinical findings. "
        "Preserve all exact medicine names, doses, units, and test values:\n\n"
        f"```json\n{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}\n```"
    )

    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TeluguHealthSummary,
        temperature=0.1,
        system_instruction=TELUGU_SYSTEM_INSTRUCTION,
    )

    models_to_try = [model_name]
    for fb in FALLBACK_MODELS:
        if fb not in models_to_try:
            models_to_try.append(fb)

    response = None
    used_model = model_name

    for idx, current_model in enumerate(models_to_try):
        logger.info(
            "Calling Gemini model %s for Telugu explanation",
            current_model,
        )
        try:
            response = client.models.generate_content(
                model=current_model,
                contents=user_prompt,
                config=gen_config,
            )
            used_model = current_model
            break
        except errors.APIError as exc:
            code = getattr(exc, "code", 500)
            message = str(getattr(exc, "message", None) or exc or "")
            clean_diag = _clean_api_error_message(message)
            logger.warning(
                "Gemini API error during Telugu explanation on %s: HTTP %s (%s)",
                current_model,
                code,
                clean_diag,
            )

            if code in (401, 403) or "API_KEY_INVALID" in message:
                raise GeminiConfigError(
                    "Invalid Gemini API key provided. Check GEMINI_API_KEY in backend/.env."
                ) from exc

            if code == 429 or "RESOURCE_EXHAUSTED" in message or "429" in str(code):
                raise GeminiRateLimitError(
                    "Gemini API rate limit or quota exceeded. Please try again shortly."
                ) from exc

            is_recoverable_status = (
                code in (404, 503)
                or "NOT_FOUND" in message
                or "UNAVAILABLE" in message
            )
            if is_recoverable_status and idx < len(models_to_try) - 1:
                logger.warning(
                    "Model %s returned HTTP %s. Falling back to %s for Telugu explanation.",
                    current_model,
                    code,
                    models_to_try[idx + 1],
                )
                continue

            if code == 404 or "NOT_FOUND" in message:
                detail = clean_diag or "Model is no longer available or was not found."
                raise GeminiApiError(
                    f"Gemini API request failed (HTTP 404): Model '{current_model}' is unavailable. {detail}"
                ) from exc
            if code == 503 or "UNAVAILABLE" in message:
                detail = clean_diag or "Model is currently experiencing high demand."
                raise GeminiApiError(
                    f"Gemini API request failed (HTTP 503): {detail}"
                ) from exc

            raise GeminiApiError(
                f"Gemini API request failed (HTTP {code})"
                + (f": {clean_diag}" if clean_diag else ".")
            ) from exc
        except Exception as exc:
            logger.warning(
                "Unexpected error during Telugu explanation: %s", type(exc).__name__
            )
            if idx < len(models_to_try) - 1:
                continue
            raise GeminiApiError(
                "Could not connect to Gemini service for Telugu translation."
            ) from exc

    if response is None:
        raise GeminiApiError(
            "Failed to receive response from Gemini for Telugu explanation."
        )

    raw_response_text = getattr(response, "text", None)
    if not raw_response_text or not raw_response_text.strip():
        logger.warning("Gemini returned empty response for Telugu explanation.")
        raise GeminiInvalidOutputError("Gemini returned an empty Telugu response.")

    try:
        summary = TeluguHealthSummary.model_validate_json(raw_response_text)
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.warning(
            "Failed to validate Telugu response against schema: %s", type(exc).__name__
        )
        raise GeminiInvalidOutputError(
            "Model response could not be validated against Telugu schema."
        ) from exc

    summary.model_used = used_model
    return summary
