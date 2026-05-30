import type { Cell, CellStatus, LockStatus } from "./cell";

export type OperationType = "LOAD" | "UNLOAD" | "REPLACE";

export type OperationStatus =
  | "CREATED"
  | "CELL_OPEN_COMMAND_SENT"
  | "WAITING_CELL_OPEN"
  | "WAITING_COURIER_ACTION"
  | "WAITING_CELL_CLOSE"
  | "READY_TO_CONFIRM"
  | "WAITING_CONFIRMATION"
  | "COMPLETED"
  | "CANCELLED"
  | "FAILED";

export const TERMINAL_STATUSES: ReadonlySet<OperationStatus> = new Set<OperationStatus>([
  "COMPLETED",
  "CANCELLED",
  "FAILED",
]);

/** Shape returned by workflow-step endpoints and by .../status. */
export interface OperationStep {
  operation_id: number;
  operation_type: OperationType;
  operation_status: OperationStatus;
  cell_number: number;
  cell_status: CellStatus;
  lock_status: LockStatus;
  message: string;
}

export interface CourierOperationView {
  id: number;
  operation_type: OperationType;
  status: OperationStatus;
  cell_number: number;
}

export interface ConfirmResponse {
  message: string;
  cell: Cell;
}

export interface LoadStartRequest {
  cell_number: number;
  product_id: string;
  product_name: string;
  product_price: number;
}

export interface ReplaceStartRequest {
  cell_number: number;
  new_product_id: string;
  new_product_name: string;
  new_product_price: number;
}
