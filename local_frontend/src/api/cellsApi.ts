import type { Cell } from "../types/cell";
import { createCells } from "../types/cell";

export async function fetchCells(): Promise<Cell[]> {
  return createCells();
}

export async function selectCell(cellId: number): Promise<{ ok: true; cellId: number }> {
  return { ok: true, cellId };
}
