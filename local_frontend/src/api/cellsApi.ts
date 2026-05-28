import type { Cell, OpenCellResponse } from "../types/cell";
import { createCells } from "../types/cell";

const API_BASE_URL = "http://127.0.0.1:8000/api";

export async function fetchCells(): Promise<Cell[]> {
  return createCells();
}

export async function openCell(cellNumber: number): Promise<OpenCellResponse> {
  const response = await fetch(`${API_BASE_URL}/cells/${cellNumber}/open`, {
    method: "POST",
  });

  if (!response.ok && response.status !== 400 && response.status !== 503) {
    throw new Error("Backend unavailable");
  }

  return response.json() as Promise<OpenCellResponse>;
}
