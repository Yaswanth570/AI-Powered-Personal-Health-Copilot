/** API Client for SaaS Authentication and Session Management (Phase 3).
 *
 * Provides endpoints and token management for:
 * - User Registration: POST /api/auth/register
 * - User Login: POST /api/auth/login
 * - Current User Profile: GET /api/auth/me
 * - Bearer Token Header Injection for all protected requests
 * - 401 Unauthorized event dispatch for automatic session expiration
 */

import type { AuthTokenResponse, AuthUser, LoginPayload, RegisterPayload } from "../types";
import { getApiBaseUrl } from "./pdfApi";

const TOKEN_STORAGE_KEY = "health_copilot_jwt_token";
const UNAUTHORIZED_EVENT = "health_copilot_auth_unauthorized";

export class AuthApiError extends Error {
  public readonly status: number;
  public readonly details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.details = details;
  }
}

/** Retrieve the current stored JWT access token from localStorage. */
export function getAuthToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Persist a JWT access token to localStorage. */
export function setAuthToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } catch (err) {
    console.error("Failed to persist authentication token:", err);
  }
}

/** Clear the persisted JWT access token from localStorage. */
export function clearAuthToken(): void {
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch (err) {
    console.error("Failed to clear authentication token:", err);
  }
}

/** Return HTTP headers with Authorization: Bearer <token> attached if token is present. */
export function getAuthHeaders(headers: HeadersInit = {}): HeadersInit {
  const token = getAuthToken();
  const baseHeaders: Record<string, string> = {};

  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      baseHeaders[key] = value;
    });
  } else if (Array.isArray(headers)) {
    headers.forEach(([key, value]) => {
      baseHeaders[key] = value;
    });
  } else if (typeof headers === "object" && headers !== null) {
    Object.assign(baseHeaders, headers);
  }

  if (token) {
    baseHeaders["Authorization"] = `Bearer ${token}`;
  }

  return baseHeaders;
}

/** Broadcast an event when a 401 Unauthorized response is encountered. */
export function notifyUnauthorized(): void {
  clearAuthToken();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
  }
}

/** Subscribe to session expiration / 401 events. Returns an unsubscribe cleanup function. */
export function onUnauthorized(callback: () => void): () => void {
  if (typeof window === "undefined") {
    return () => {};
  }
  const handler = () => callback();
  window.addEventListener(UNAUTHORIZED_EVENT, handler);
  return () => {
    window.removeEventListener(UNAUTHORIZED_EVENT, handler);
  };
}

async function handleAuthResponse<T>(res: Response, defaultMessage: string): Promise<T> {
  if (res.ok) {
    return (await res.json()) as T;
  }

  if (res.status === 401) {
    notifyUnauthorized();
  }

  let errorDetail = defaultMessage;
  let rawJson: unknown;
  try {
    rawJson = await res.json();
    if (rawJson && typeof rawJson === "object" && "detail" in rawJson) {
      const detail = (rawJson as { detail: unknown }).detail;
      if (typeof detail === "string") {
        errorDetail = detail;
      } else if (Array.isArray(detail)) {
        // Pydantic validation error array
        errorDetail = detail.map((d: { msg?: string }) => d.msg || "Invalid input").join("; ");
      }
    }
  } catch {
    // response body is not JSON
  }

  throw new AuthApiError(errorDetail, res.status, rawJson);
}

/** Register a new user account with real backend password hashing and primary patient creation. */
export async function registerUser(payload: RegisterPayload): Promise<AuthTokenResponse> {
  const url = `${getApiBaseUrl()}/api/auth/register`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await handleAuthResponse<AuthTokenResponse>(res, "Registration failed");
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

/** Authenticate an existing user with real backend credentials and obtain signed JWT. */
export async function loginUser(payload: LoginPayload): Promise<AuthTokenResponse> {
  const url = `${getApiBaseUrl()}/api/auth/login`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const data = await handleAuthResponse<AuthTokenResponse>(res, "Login failed");
  if (data.access_token) {
    setAuthToken(data.access_token);
  }
  return data;
}

/** Fetch current authenticated user's profile using the stored Bearer token. */
export async function fetchCurrentUser(): Promise<AuthUser> {
  const token = getAuthToken();
  if (!token) {
    throw new AuthApiError("No authentication token available", 401);
  }

  const url = `${getApiBaseUrl()}/api/auth/me`;
  const res = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders({ "Content-Type": "application/json" }),
  });

  return handleAuthResponse<AuthUser>(res, "Session verification failed");
}
