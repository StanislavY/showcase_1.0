import type {
  ConfirmResponse,
  CourierOperationView,
  LoadStartRequest,
  OperationStep,
  ReplaceStartRequest,
} from "../types/operation";
import { apiFetch } from "./client";

export function startLoad(request: LoadStartRequest): Promise<OperationStep> {
  return apiFetch<OperationStep>("/courier/operations/load/start", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function startUnload(cellNumber: number): Promise<OperationStep> {
  return apiFetch<OperationStep>("/courier/operations/unload/start", {
    method: "POST",
    body: JSON.stringify({ cell_number: cellNumber }),
  });
}

export function startReplace(request: ReplaceStartRequest): Promise<OperationStep> {
  return apiFetch<OperationStep>("/courier/operations/replace/start", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function refreshLockStatus(operationId: number): Promise<OperationStep> {
  return apiFetch<OperationStep>(
    `/courier/operations/${operationId}/refresh-lock-status`,
    { method: "POST" },
  );
}

export function courierActionDone(operationId: number): Promise<OperationStep> {
  return apiFetch<OperationStep>(
    `/courier/operations/${operationId}/courier-action-done`,
    { method: "POST" },
  );
}

export function confirmOperation(operationId: number): Promise<ConfirmResponse> {
  return apiFetch<ConfirmResponse>(
    `/courier/operations/${operationId}/confirm`,
    { method: "POST" },
  );
}

export function cancelOperation(operationId: number): Promise<OperationStep> {
  return apiFetch<OperationStep>(
    `/courier/operations/${operationId}/cancel`,
    { method: "POST" },
  );
}

export function getOperationStatus(operationId: number): Promise<OperationStep> {
  return apiFetch<OperationStep>(
    `/courier/operations/${operationId}/status`,
    { method: "GET" },
  );
}

export function listActiveOperations(): Promise<CourierOperationView[]> {
  return apiFetch<CourierOperationView[]>("/courier/operations/active", {
    method: "GET",
  });
}
