import type { Cell, OpenCellResponse } from "../types/cell";
import { apiFetch } from "./client";

export function fetchCells(): Promise<Cell[]> {
  return apiFetch<Cell[]>("/cells", { method: "GET" });
}

/** Dispatch an "open" command for a single cell (write-only on the backend). */
export function openCell(cellNumber: number): Promise<OpenCellResponse> {
  return apiFetch<OpenCellResponse>(`/cells/${cellNumber}/open`, {
    method: "POST",
  });
}
