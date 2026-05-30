import type { CellStatus, LockStatus } from "./types/cell";
import type { OperationStatus, OperationType } from "./types/operation";

type ChipColor = "default" | "primary" | "success" | "warning" | "error" | "info";

export const CELL_STATUS_LABEL: Record<CellStatus, string> = {
  EMPTY: "Пустая",
  LOADED: "С товаром",
  SERVICE: "Обслуживание",
  BLOCKED: "Заблокирована",
  ERROR: "Ошибка",
};

export const CELL_STATUS_COLOR: Record<CellStatus, ChipColor> = {
  EMPTY: "default",
  LOADED: "info",
  SERVICE: "warning",
  BLOCKED: "error",
  ERROR: "error",
};

export const LOCK_STATUS_LABEL: Record<LockStatus, string> = {
  UNKNOWN: "Неизвестно",
  OPEN: "Открыт",
  CLOSED: "Закрыт",
  ERROR: "Ошибка",
};

export const LOCK_STATUS_COLOR: Record<LockStatus, ChipColor> = {
  UNKNOWN: "default",
  OPEN: "warning",
  CLOSED: "success",
  ERROR: "error",
};

export const OPERATION_TYPE_LABEL: Record<OperationType, string> = {
  LOAD: "Загрузка товара",
  UNLOAD: "Выгрузка товара",
  REPLACE: "Замена товара",
};

/** Big, courier-facing hint for the current step of the operation. */
export function operationHint(
  status: OperationStatus,
  type: OperationType,
): string {
  switch (status) {
    case "CREATED":
    case "CELL_OPEN_COMMAND_SENT":
    case "WAITING_CELL_OPEN":
      return "Ожидаем открытия замка";
    case "WAITING_COURIER_ACTION":
      if (type === "LOAD") return "Положите товар";
      if (type === "UNLOAD") return "Заберите товар";
      return "Замените товар";
    case "WAITING_CELL_CLOSE":
    case "WAITING_CONFIRMATION":
      return "Закройте ячейку";
    case "READY_TO_CONFIRM":
      return "Можно подтвердить операцию";
    case "COMPLETED":
      return "Операция завершена";
    case "CANCELLED":
      return "Операция отменена";
    case "FAILED":
      return "Операция завершилась ошибкой";
    default:
      return status;
  }
}
