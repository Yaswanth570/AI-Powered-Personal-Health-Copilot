"""API endpoints for Personal Health AI Copilot conversational chat (Step 9).

Provides:
- Patient-isolated conversation management (create, list, get, delete).
- Real-time conversational queries grounded in verified medical records.
- Citation tracking linking answers to original lab tests and prescriptions.
- Safe model fallbacks and error handling.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db.models import ChatConversation, ChatMessage, Patient
from ..db.session import get_db
from ..schemas import (
    ChatCitationItem,
    ChatConversationCreate,
    ChatConversationDetail,
    ChatConversationSummary,
    ChatMessageResponse,
    ChatSendMessageRequest,
    ChatSendMessageResponse,
)
from ..services.gemini_extractor import (
    GeminiApiError,
    GeminiConfigError,
    GeminiInvalidOutputError,
    GeminiRateLimitError,
    _clean_api_error_message,
)
from ..services.health_copilot_chat import (
    generate_copilot_chat_response,
    retrieve_patient_clinical_context,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/patients/{patient_id}", tags=["health-ai-chat"])


def _verify_patient(db: Session, patient_id: str) -> Patient:
    """Verify that the patient exists in the database.

    Enforces patient existence before performing conversation operations.
    """
    patient = db.scalar(select(Patient).where(Patient.id == patient_id))
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return patient


def _verify_conversation(
    db: Session, patient_id: str, conversation_id: str
) -> ChatConversation:
    """Verify that the conversation exists and strictly belongs to the specified patient.

    Prevents cross-patient unauthorized data access and conversation leakage.
    """
    conv = db.scalar(
        select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.patient_id == patient_id,
        )
    )
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found for patient '{patient_id}'.",
        )
    return conv


def _parse_citations(raw: Any) -> list[ChatCitationItem] | None:
    """Safely deserialize citations list from dict, JSON string, or ChatCitationItem."""
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if isinstance(raw, list):
        items: list[ChatCitationItem] = []
        for c in raw:
            if isinstance(c, dict):
                try:
                    items.append(ChatCitationItem(**c))
                except Exception:
                    pass
            elif isinstance(c, ChatCitationItem):
                items.append(c)
        return items if items else None
    return None


@router.get("/conversations", response_model=list[ChatConversationSummary])
def list_conversations(
    patient_id: str,
    db: Session = Depends(get_db),
) -> list[ChatConversationSummary]:
    """List all chat conversations for the active patient, ordered by last activity."""
    _verify_patient(db, patient_id)

    conversations = db.scalars(
        select(ChatConversation)
        .where(ChatConversation.patient_id == patient_id)
        .order_by(ChatConversation.updated_at.desc())
    ).all()

    summaries: list[ChatConversationSummary] = []
    for conv in conversations:
        # Message count
        count = db.scalar(
            select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
        ) or 0

        # Last message preview
        last_msg = db.scalar(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conv.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        preview = None
        if last_msg:
            clean_text = last_msg.content.strip().replace("\n", " ")
            preview = clean_text[:120] + ("..." if len(clean_text) > 120 else "")

        summaries.append(
            ChatConversationSummary(
                id=conv.id,
                patient_id=conv.patient_id,
                title=conv.title,
                message_count=count,
                last_message_preview=preview,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
        )

    return summaries


@router.post(
    "/conversations",
    response_model=ChatConversationDetail,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    patient_id: str,
    payload: ChatConversationCreate | None = None,
    db: Session = Depends(get_db),
) -> ChatConversationDetail:
    """Create a new conversational consultation session for the patient."""
    _verify_patient(db, patient_id)

    title = (payload.title.strip() if payload and payload.title and payload.title.strip() else None) or "Health Consultation"

    now = datetime.now(timezone.utc)
    conv = ChatConversation(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        title=title,
        created_at=now,
        updated_at=now,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    return ChatConversationDetail(
        id=conv.id,
        patient_id=conv.patient_id,
        title=conv.title,
        messages=[],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/conversations/{conversation_id}", response_model=ChatConversationDetail)
def get_conversation(
    patient_id: str,
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ChatConversationDetail:
    """Retrieve an existing conversation along with its chronological message history."""
    _verify_patient(db, patient_id)
    conv = _verify_conversation(db, patient_id, conversation_id)

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.asc())
    ).all()

    msg_responses: list[ChatMessageResponse] = [
        ChatMessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            citations=_parse_citations(m.citations),
            model_used=m.model_used,
            created_at=m.created_at,
        )
        for m in messages
    ]

    return ChatConversationDetail(
        id=conv.id,
        patient_id=conv.patient_id,
        title=conv.title,
        messages=msg_responses,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(
    patient_id: str,
    conversation_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a conversation and all of its associated messages."""
    _verify_patient(db, patient_id)
    conv = _verify_conversation(db, patient_id, conversation_id)
    db.delete(conv)
    db.commit()
    return {"deleted": True, "conversation_id": conversation_id}


def _execute_chat_message(
    db: Session,
    patient_id: str,
    conversation_id: str,
    user_query: str,
    settings: Settings,
) -> ChatSendMessageResponse:
    """Execute sending a chat message, calling Gemini, saving messages, and returning response."""
    conv = _verify_conversation(db, patient_id, conversation_id)

    now = datetime.now(timezone.utc)

    # 1. Reuse existing unreplied or retried user message to prevent duplicates on retries
    recent_messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(2)
    ).all()

    existing_assistant: ChatMessage | None = None
    user_msg: ChatMessage | None = None

    if (
        len(recent_messages) >= 1
        and recent_messages[0].role == "user"
        and recent_messages[0].content.strip() == user_query.strip()
    ):
        # Case 1: Unreplied user query (e.g. prior attempt failed before assistant replied)
        user_msg = recent_messages[0]
    elif (
        len(recent_messages) >= 2
        and recent_messages[0].role == "assistant"
        and recent_messages[1].role == "user"
        and recent_messages[1].content.strip() == user_query.strip()
    ):
        # Case 2: Exact re-send / retry of the last completed turn
        user_msg = recent_messages[1]
        existing_assistant = recent_messages[0]
    else:
        # Case 3: Fresh message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="user",
            content=user_query,
            created_at=now,
        )
        db.add(user_msg)
        db.flush()

    # 2. Retrieve chronological prior conversation history (up to last 12 messages)
    prior_filter = [
        ChatMessage.conversation_id == conv.id,
        ChatMessage.id != user_msg.id,
    ]
    if existing_assistant:
        prior_filter.append(ChatMessage.id != existing_assistant.id)

    prior_messages = db.scalars(
        select(ChatMessage)
        .where(*prior_filter)
        .order_by(ChatMessage.created_at.asc())
    ).all()

    history_pydantic: list[ChatMessageResponse] = [
        ChatMessageResponse(
            id=m.id,
            conversation_id=m.conversation_id,
            role=m.role,
            content=m.content,
            citations=_parse_citations(m.citations),
            model_used=m.model_used,
            created_at=m.created_at,
        )
        for m in prior_messages[-12:]
    ]

    # 3. Retrieve verified patient medical context (diagnoses, medications, lab tests, documents)
    patient_context = retrieve_patient_clinical_context(db, patient_id)

    # 4. Invoke Gemini with bounded retries, fallback cascade, and safety guardrails
    try:
        ai_reply = generate_copilot_chat_response(
            patient_context=patient_context,
            conversation_history=history_pydantic,
            user_query=user_query,
            settings=settings,
        )
    except GeminiConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GeminiRateLimitError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except GeminiInvalidOutputError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except GeminiApiError as exc:
        db.rollback()
        err_msg = str(exc)
        err_lower = err_msg.lower()
        if "high demand" in err_lower or "503" in err_lower or "unavailable" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Health AI Copilot is temporarily experiencing high demand across all models. Please retry in a few moments.",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=_clean_api_error_message(err_msg),
        ) from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error in health copilot chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate copilot response. Please retry.",
        ) from exc

    # 5. Save or update assistant reply in database with actual successful model recorded
    assistant_now = datetime.now(timezone.utc)
    citations_data = [c.model_dump() for c in ai_reply.citations]
    if existing_assistant:
        existing_assistant.content = ai_reply.answer_markdown
        existing_assistant.citations = citations_data
        existing_assistant.model_used = ai_reply.model_used or settings.gemini_model
        existing_assistant.created_at = assistant_now
        assistant_msg = existing_assistant
    else:
        assistant_msg = ChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="assistant",
            content=ai_reply.answer_markdown,
            citations=citations_data,
            model_used=ai_reply.model_used or settings.gemini_model,
            created_at=assistant_now,
        )
        db.add(assistant_msg)

    # 6. Update conversation timestamp and title if needed
    conv.updated_at = assistant_now
    if conv.title == "Health Consultation":
        # Formulate a concise title from the user query
        words = user_query.strip().split()
        if words:
            snippet = " ".join(words[:6])
            conv.title = snippet[:60].capitalize()

    db.commit()

    return ChatSendMessageResponse(
        conversation_id=conv.id,
        user_message=ChatMessageResponse(
            id=user_msg.id,
            conversation_id=conv.id,
            role=user_msg.role,
            content=user_msg.content,
            citations=None,
            model_used=None,
            created_at=user_msg.created_at,
        ),
        assistant_message=ChatMessageResponse(
            id=assistant_msg.id,
            conversation_id=conv.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            citations=ai_reply.citations,
            model_used=assistant_msg.model_used,
            created_at=assistant_msg.created_at,
        ),
        suggested_follow_ups=ai_reply.suggested_follow_ups,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatSendMessageResponse,
)
def send_conversation_message(
    patient_id: str,
    conversation_id: str,
    payload: ChatSendMessageRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChatSendMessageResponse:
    """Send a user message in an existing conversation and receive an evidence-grounded AI reply."""
    _verify_patient(db, patient_id)
    user_query = payload.message.strip()
    if not user_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    return _execute_chat_message(
        db=db,
        patient_id=patient_id,
        conversation_id=conversation_id,
        user_query=user_query,
        settings=settings,
    )


@router.post("/chat", response_model=ChatSendMessageResponse)
def quick_chat(
    patient_id: str,
    payload: ChatSendMessageRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ChatSendMessageResponse:
    """Convenience endpoint: send a message, auto-creating a conversation if none specified."""
    _verify_patient(db, patient_id)

    user_query = payload.message.strip()
    if not user_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty.",
        )

    conversation_id = payload.conversation_id
    if not conversation_id:
        # Create a new conversation
        words = user_query.split()
        snippet = " ".join(words[:6]) if words else "Health Consultation"
        title = snippet[:60].capitalize()

        now = datetime.now(timezone.utc)
        conv = ChatConversation(
            id=str(uuid.uuid4()),
            patient_id=patient_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        db.add(conv)
        db.commit()
        conversation_id = conv.id

    return _execute_chat_message(
        db=db,
        patient_id=patient_id,
        conversation_id=conversation_id,
        user_query=user_query,
        settings=settings,
    )
