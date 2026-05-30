import type { AdminLoginResponse } from "../types/auth";
import { API_BASE_URL } from "./client";

const BACKEND_UNAVAILABLE = "Локальный backend недоступен";

/** Pull a human-readable message out of an error body, if present.
 *
 * On a 401 the backend nests the login response under ``detail``
 * (FastAPI's HTTPException shape), so we look there first.
 */
function extractMessage(data: unknown): string | null {
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    const detail = obj.detail;
    if (detail && typeof detail === "object") {
      const message = (detail as Record<string, unknown>).message;
      if (typeof message === "string") return message;
    }
    if (typeof obj.message === "string") return obj.message;
    if (typeof obj.detail === "string") return obj.detail;
  }
  return null;
}

/**
 * Send the admin password to the backend for verification.
 *
 * The password is never compared on the frontend — the backend owns the
 * check and issues a session token on success.
 */
export async function loginAdmin(
  password: string,
): Promise<AdminLoginResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/admin/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });
  } catch {
    throw new Error(BACKEND_UNAVAILABLE);
  }

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (response.status === 401) {
    return {
      success: false,
      token: null,
      admin_id: null,
      message: extractMessage(data) ?? "Неверный пароль администратора",
    };
  }

  if (!response.ok) {
    throw new Error(extractMessage(data) ?? BACKEND_UNAVAILABLE);
  }

  return data as AdminLoginResponse;
}

/** Return true if the stored admin session token is still valid. */
export async function checkAdminSession(token: string): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/admin/auth/check`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.ok;
  } catch {
    return false;
  }
}
