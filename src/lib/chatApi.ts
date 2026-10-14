/** API Client for Personal Health AI Copilot conversational chat (Step 9).
 *
 * Interacts with FastAPI backend endpoints:
 * - GET /api/patients/{patient_id}/conversations
 * - POST /api/patients/{patient_id}/conversations
 * - GET /api/patients/{patient_id}/conversations/{conversation_id}
 * - DELETE /api/patients/{patient_id}/conversations/{conversation_id}
 * - POST /api/patients/{patient_id}/conversations/{conversation_id}/messages
 * - POST /api/patients/{patient_id}/chat
 */

import type {
  ChatConversationDetail,
  ChatConversationSummary,
  ChatSendMessageResponse,
} from "../types";
import { getAuthHeaders, notifyUnauthorized } from "./authApi";
import { getApiBaseUrl } from "./pdfApi";

export class ChatApiError extends Error {
  public readonly status: number;
  public readonly details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ChatApiError";
    this.status = status;
    this.details = details;
  }
}

async function handleResponse<T>(res: Response, defaultMessage: string): Promise<T> {
  if (res.status === 401) {
    notifyUnauthorized();
  }

  if (res.ok) {
    return (await res.json()) as T;
  }

  let errorDetail = defaultMessage;
  let rawJson: unknown;
  try {
    rawJson = await res.json();
    if (rawJson && typeof rawJson === "object" && "detail" in rawJson) {
      errorDetail = String((rawJson as { detail: unknown }).detail);
    }
  } catch {
    // response is not JSON
  }

  throw new ChatApiError(
    `${defaultMessage} (HTTP ${res.status}): ${errorDetail}`,
    res.status,
    rawJson,
  );
}

/** Fetch all conversations for the patient. */
export async function fetchConversations(
  patientId: string,
): Promise<ChatConversationSummary[]> {
  const url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/conversations`;
  const res = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<ChatConversationSummary[]>(res, "Failed to load conversations");
}

/** Create a new consultation conversation session. */
export async function createConversation(
  patientId: string,
  title?: string,
): Promise<ChatConversationDetail> {
  const url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/conversations`;
  const res = await fetch(url, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ title }),
  });
  return handleResponse<ChatConversationDetail>(res, "Failed to create conversation");
}

/** Fetch details and full message history of an existing conversation. */
export async function fetchConversation(
  patientId: string,
  conversationId: string,
): Promise<ChatConversationDetail> {
  const url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/conversations/${encodeURIComponent(conversationId)}`;
  const res = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<ChatConversationDetail>(res, "Failed to load conversation history");
}

/** Delete a conversation and all its messages. */
export async function deleteConversation(
  patientId: string,
  conversationId: string,
): Promise<void> {
  const url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/conversations/${encodeURIComponent(conversationId)}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  await handleResponse<{ deleted: boolean }>(res, "Failed to delete conversation");
}

/** Send a message and receive an evidence-grounded AI reply. */
export async function sendChatMessage(
  patientId: string,
  conversationId: string | null,
  message: string,
): Promise<ChatSendMessageResponse> {
  let url: string;
  let body: Record<string, unknown>;

  if (conversationId) {
    url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/conversations/${encodeURIComponent(conversationId)}/messages`;
    body = { message, conversation_id: conversationId };
  } else {
    url = `${getApiBaseUrl()}/api/patients/${encodeURIComponent(patientId)}/chat`;
    body = { message };
  }

  const res = await fetch(url, {
    method: "POST",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });

  return handleResponse<ChatSendMessageResponse>(res, "Failed to send chat message");
}
