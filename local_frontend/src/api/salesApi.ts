import { API_BASE_URL, apiFetch } from "./client";
import type { SaleResponse, SalesLimitSummary } from "../types/sales";

const BACKEND_UNAVAILABLE =
  "Локальный backend недоступен. Обратитесь к администратору";

/** Read the current sales limit (public endpoint). */
export async function fetchSalesLimit(): Promise<SalesLimitSummary> {
  return apiFetch<SalesLimitSummary>("/sales/limit");
}

/**
 * Set a new sales limit (admin only).
 *
 * The amount is in kopecks. A valid admin bearer token is required; the
 * backend closes the previous active limit and opens a fresh one. On a
 * backend error the rejected promise carries the backend's Russian message.
 */
export async function setSalesLimit(
  limitAmountKopecks: number,
  token: string,
): Promise<SalesLimitSummary> {
  return apiFetch<SalesLimitSummary>("/admin/sales/limit", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ limit_amount_kopecks: limitAmountKopecks }),
  });
}

/**
 * Buy the product in ``cellNumber`` via the sales endpoint.
 *
 * The backend returns the same {@link SaleResponse} shape on success and
 * on business-rule failures (empty cell, exhausted limit, hardware error),
 * just with different HTTP status codes — so we resolve with the parsed
 * body in both cases and let the caller branch on ``success``. Only a
 * network failure rejects, with the "backend unavailable" message.
 */
export async function sellFromCell(cellNumber: number): Promise<SaleResponse> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE_URL}/sales/cells/${cellNumber}/sell`,
      { method: "POST", headers: { "Content-Type": "application/json" } },
    );
  } catch {
    throw new Error(BACKEND_UNAVAILABLE);
  }

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (data && typeof data === "object" && "success" in data) {
    return data as SaleResponse;
  }

  // Unexpected body (e.g. raw FastAPI validation error): surface a message.
  const message =
    data && typeof data === "object" && "detail" in data
      ? String((data as Record<string, unknown>).detail)
      : BACKEND_UNAVAILABLE;
  return { success: false, message, sale: null, limit_summary: null };
}
