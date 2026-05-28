export interface Cell {
  id: number;
}

export const TOTAL_CELLS = 27;

export function createCells(total: number = TOTAL_CELLS): Cell[] {
  return Array.from({ length: total }, (_, index) => ({ id: index + 1 }));
}
