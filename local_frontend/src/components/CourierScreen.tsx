import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import LogoutIcon from "@mui/icons-material/Logout";
import RefreshIcon from "@mui/icons-material/Refresh";
import { fetchCells } from "../api/cellsApi";
import {
  cancelOperation,
  confirmOperation,
  courierActionDone,
  getOperationStatus,
  listActiveOperations,
  refreshLockStatus,
  startLoad,
  startReplace,
  startUnload,
} from "../api/courierApi";
import { ApiError } from "../api/client";
import { CellGrid } from "./CellGrid";
import { CELL_STATUS_LEGEND, CELL_STATUS_TONES } from "./cellStatusView";
import {
  glassButtonSx,
  glassPanelSx,
  kioskHeaderSx,
  kioskRootSx,
  kioskSubtitleSx,
  kioskTitleSx,
  KIOSK_TEXT,
} from "./kioskScreenStyles";
import { OperationPanel } from "./OperationPanel";
import { StartOperationDialog } from "./StartOperationDialog";
import type { Cell } from "../types/cell";
import type {
  LoadStartRequest,
  OperationStep,
  ReplaceStartRequest,
} from "../types/operation";
import { TERMINAL_STATUSES } from "../types/operation";

interface CourierScreenProps {
  courierId: string;
  onLogout: () => void;
}

type Banner = { severity: "success" | "warning" | "error"; text: string };

function toMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Неизвестная ошибка. Повторите попытку.";
}

export function CourierScreen({ courierId, onLogout }: CourierScreenProps) {
  const [cells, setCells] = useState<Cell[]>([]);
  const [loadingCells, setLoadingCells] = useState(true);
  const [activeOp, setActiveOp] = useState<OperationStep | null>(null);
  const [selectedCell, setSelectedCell] = useState<Cell | null>(null);
  const [busy, setBusy] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);
  const [banner, setBanner] = useState<Banner | null>(null);

  const loadCells = useCallback(async () => {
    setCells(await fetchCells());
  }, []);

  const bootstrap = useCallback(async () => {
    setLoadingCells(true);
    try {
      const [cellsData, active] = await Promise.all([
        fetchCells(),
        listActiveOperations(),
      ]);
      setCells(cellsData);
      const ongoing = active.find((op) => !TERMINAL_STATUSES.has(op.status));
      if (ongoing) {
        setActiveOp(await getOperationStatus(ongoing.id));
      }
    } catch (error) {
      setBanner({ severity: "error", text: toMessage(error) });
    } finally {
      setLoadingCells(false);
    }
  }, []);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  const startOperation = async (fn: () => Promise<OperationStep>) => {
    setBusy(true);
    setOpError(null);
    try {
      const step = await fn();
      setActiveOp(step);
      setSelectedCell(null);
      setBanner(null);
      await loadCells();
    } catch (error) {
      setOpError(toMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const handleStartLoad = (request: LoadStartRequest) =>
    startOperation(() => startLoad(request));
  const handleStartUnload = (cellNumber: number) =>
    startOperation(() => startUnload(cellNumber));
  const handleStartReplace = (request: ReplaceStartRequest) =>
    startOperation(() => startReplace(request));

  // Re-read the operation after an error so the screen reflects the real
  // backend state; if it became terminal, leave the operation screen.
  const syncAfterError = async (operationId: number) => {
    try {
      const step = await getOperationStatus(operationId);
      if (TERMINAL_STATUSES.has(step.operation_status)) {
        setActiveOp(null);
        setBanner({ severity: "warning", text: step.message });
        await loadCells();
      } else {
        setActiveOp(step);
      }
    } catch {
      /* keep the current view; the error alert is already shown */
    }
  };

  const runStep = async (fn: () => Promise<OperationStep>) => {
    if (!activeOp) return;
    const operationId = activeOp.operation_id;
    setBusy(true);
    setOpError(null);
    try {
      const step = await fn();
      await loadCells();
      if (TERMINAL_STATUSES.has(step.operation_status)) {
        setActiveOp(null);
        setBanner({ severity: "warning", text: step.message });
      } else {
        setActiveOp(step);
      }
    } catch (error) {
      setOpError(toMessage(error));
      await syncAfterError(operationId);
    } finally {
      setBusy(false);
    }
  };

  const handleRefreshLock = () =>
    runStep(() => refreshLockStatus(activeOp!.operation_id));
  const handleActionDone = () =>
    runStep(() => courierActionDone(activeOp!.operation_id));

  const handleConfirm = async () => {
    if (!activeOp) return;
    const operationId = activeOp.operation_id;
    setBusy(true);
    setOpError(null);
    try {
      const result = await confirmOperation(operationId);
      setActiveOp(null);
      await loadCells();
      setBanner({ severity: "success", text: result.message });
    } catch (error) {
      // Confirm rejected (e.g. lock still open) — NOT a success.
      setOpError(toMessage(error));
      await syncAfterError(operationId);
    } finally {
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    if (!activeOp) return;
    const operationId = activeOp.operation_id;
    setBusy(true);
    setOpError(null);
    try {
      const step = await cancelOperation(operationId);
      setActiveOp(null);
      await loadCells();
      setBanner({ severity: "warning", text: step.message });
    } catch (error) {
      // Cancel rejected (e.g. lock open) — do NOT treat as cancelled.
      setOpError(toMessage(error));
      await syncAfterError(operationId);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={kioskRootSx}>
      <Box component="header" sx={kioskHeaderSx}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h4" sx={kioskTitleSx}>
            Экран курьера — постамат
          </Typography>
          {courierId !== "" && (
            <Typography variant="body2" sx={kioskSubtitleSx}>
              Курьер: {courierId}
            </Typography>
          )}
        </Box>
        <Button
          variant="contained"
          startIcon={<LogoutIcon />}
          onClick={onLogout}
          disabled={busy}
          disableElevation
          sx={glassButtonSx}
        >
          Выйти из режима курьера
        </Button>
      </Box>

      <Container maxWidth="xl" sx={{ pt: { xs: 1, md: 1.5 }, pb: { xs: 2, md: 3 } }}>
        {banner !== null && (
          <Alert
            severity={banner.severity}
            sx={{ mb: 2 }}
            onClose={() => setBanner(null)}
          >
            {banner.text}
          </Alert>
        )}

        {loadingCells ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress />
          </Box>
        ) : activeOp !== null ? (
          <OperationPanel
            step={activeOp}
            busy={busy}
            error={opError}
            onRefreshLock={handleRefreshLock}
            onActionDone={handleActionDone}
            onConfirm={handleConfirm}
            onCancel={handleCancel}
          />
        ) : (
          <Box sx={glassPanelSx}>
            <Box
              sx={{
                mb: 2,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 2,
                flexWrap: "wrap",
              }}
            >
              <Typography
                variant="h6"
                sx={{ fontWeight: 700, color: "#1c2f42" }}
              >
                Выберите ячейку для операции
              </Typography>
              <Button
                onClick={() => void loadCells()}
                disabled={busy}
                startIcon={<RefreshIcon />}
                disableElevation
                sx={{
                  textTransform: "none",
                  fontWeight: 600,
                  color: KIOSK_TEXT,
                  bgcolor: "rgba(255, 255, 255, 0.9)",
                  borderRadius: "14px",
                  px: 2,
                  py: 0.85,
                  border: "1px solid rgba(180, 205, 200, 0.55)",
                  boxShadow: "0 6px 16px rgba(26, 47, 66, 0.08)",
                  "&:hover": {
                    bgcolor: "#ffffff",
                    boxShadow: "0 8px 20px rgba(26, 47, 66, 0.12)",
                  },
                }}
              >
                Обновить
              </Button>
            </Box>

            <Box
              sx={{
                mb: 2,
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: { xs: 1, sm: 2 },
                px: 1.75,
                py: 1.1,
                borderRadius: "14px",
                bgcolor: "rgba(255, 255, 255, 0.9)",
                border: "1px solid rgba(180, 205, 200, 0.45)",
                boxShadow: "0 6px 16px rgba(26, 47, 66, 0.06)",
              }}
            >
              {CELL_STATUS_LEGEND.map((entry) => (
                <Box
                  key={entry.status}
                  sx={{ display: "flex", alignItems: "center", gap: 0.75 }}
                >
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      borderRadius: "4px",
                      flexShrink: 0,
                      bgcolor: CELL_STATUS_TONES[entry.status].dot,
                    }}
                  />
                  <Typography
                    sx={{
                      fontSize: "0.8rem",
                      fontWeight: 600,
                      color: "rgba(28, 47, 66, 0.7)",
                    }}
                  >
                    {entry.label}
                  </Typography>
                </Box>
              ))}
            </Box>

            <CellGrid
              cells={cells}
              disabled={busy}
              onSelect={(cell) => {
                setOpError(null);
                setSelectedCell(cell);
              }}
            />
          </Box>
        )}
      </Container>

      <StartOperationDialog
        cell={selectedCell}
        busy={busy}
        error={opError}
        onClose={() => {
          setSelectedCell(null);
          setOpError(null);
        }}
        onStartLoad={handleStartLoad}
        onStartUnload={handleStartUnload}
        onStartReplace={handleStartReplace}
      />
    </Box>
  );
}
