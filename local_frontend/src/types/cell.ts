export type CellStatus = "EMPTY" | "LOADED" | "SERVICE" | "BLOCKED" | "ERROR";

export type LockStatus = "UNKNOWN" | "OPEN" | "CLOSED" | "ERROR";

export interface Cell {
  number: number;
  status: CellStatus;
  product_id: string | null;
  product_name: string | null;
  product_price: number | null;
  lock_status: LockStatus;
  last_lock_event_at: string | null;
  updated_at: string;
}

export const TOTAL_CELLS = 27;

/**
 * Post-dispatch state of an open command. The controller protocol is
 * write-only, so the only honest states are "command_sent" (the open
 * command was dispatched) and "dispatch_failed".
 */
export type CellOpenStatus = "command_sent" | "dispatch_failed";

export interface OpenCellResponse {
  success: boolean;
  cell_number: number;
  message: string;
  status: CellOpenStatus;
}
