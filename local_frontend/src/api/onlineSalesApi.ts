import { API_BASE_URL } from "./client";
import type { OnlineSalesPickupResponse } from "../types/onlineSales";

const BACKEND_UNAVAILABLE =
  "Локальный backend недоступен. Обратитесь к администратору";

/**
 * Trigger the online-sales pickup ("Забрать товар") scenario.
 *
 * The backend owns all business rules and always answers HTTP 200 with a
 * structured body (success / cloud offline / no products / completed /
 * partial failure). We resolve with that parsed body and let the caller
 * branch on ``code`` / ``success``. Only a genuine network failure (the
 * local backend is unreachable) rejects, with the operator-facing message.
 */
export async function pickupOnlineSale(): Promise<OnlineSalesPickupResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/online-sales/pickup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    throw new Error(BACKEND_UNAVAILABLE);
  }

  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (
    data &&
    typeof data === "object" &&
    "success" in data &&
    "code" in data &&
    "message" in data
  ) {
    return data as OnlineSalesPickupResponse;
  }

  // Unexpected body (e.g. a raw FastAPI error): surface as a backend problem.
  throw new Error(BACKEND_UNAVAILABLE);
}
