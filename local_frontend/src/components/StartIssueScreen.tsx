import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import EngineeringIcon from "@mui/icons-material/Engineering";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import { fetchCells } from "../api/cellsApi";
import { fetchSalesLimit, sellFromCell } from "../api/salesApi";
import { pickupOnlineSale } from "../api/onlineSalesApi";
import { ApiError } from "../api/client";
import { CellGrid } from "./CellGrid";
import { CELL_STATUS_LEGEND, CELL_STATUS_TONES } from "./cellStatusView";
import {
  glassButtonSx,
  glassPanelSx,
  kioskRootSx,
} from "./kioskScreenStyles";
import type { Cell } from "../types/cell";
import type { SalesLimitSummary } from "../types/sales";
import {
  ONLINE_SALES_CLOUD_UNAVAILABLE,
  type OnlineSalesPickupResponse,
} from "../types/onlineSales";
import type { TerminalMode } from "../settings/terminalMode";

interface StartIssueScreenProps {
  terminalMode: TerminalMode;
  onCourierMode: () => void;
  onAdminMode: () => void;
}

// Seconds the success result stays on screen before returning to the base
// "Забрать товар" screen.
const RETURN_TO_BASE_SECONDS = 10;

// Shown verbatim when the backend reports the cloud is unreachable, so the
// customer is told to scan the QR code instead.
const CLOUD_UNAVAILABLE_TEXT =
  "Нет интернета, отсканируйте полученный QR-код";

type Status = { severity: "info" | "success" | "error"; text: string };

const DEFAULT_STATUS: Status = {
  severity: "info",
  text: "Нажмите на ячейку с товаром, чтобы купить",
};

const CELL_NOT_SELLABLE_TEXT =
  "Эта ячейка недоступна для покупки. Выберите заполненную ячейку.";

const BACKEND_UNAVAILABLE =
  "Локальный backend недоступен. Обратитесь к администратору";

// Must match the backend message (_LIMIT_EXCEEDED_MESSAGE) exactly.
const LIMIT_EXHAUSTED_TEXT =
  "Ваш лимит закончился, обратитесь к администратору";

function toMessage(error: unknown): string {
  if (error instanceof ApiError) return BACKEND_UNAVAILABLE;
  if (error instanceof Error) return error.message;
  return BACKEND_UNAVAILABLE;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isCellSellable(cell: Cell): boolean {
  return (
    cell.status === "LOADED" &&
    cell.product_name !== null &&
    cell.product_price !== null
  );
}

/** Build the success line, naming the cells the backend reported as opened. */
function buildPickupSuccessText(result: OnlineSalesPickupResponse): string {
  const opened = result.opened_cells ?? [];
  if (opened.length > 0) {
    return `Ячейки №${opened.join(", ")} открыты. Заберите товар.`;
  }
  return result.message;
}

export function StartIssueScreen({
  terminalMode,
  onCourierMode,
  onAdminMode,
}: StartIssueScreenProps) {
  const isOnlineSales = terminalMode === "online_sales";
  const [cells, setCells] = useState<Cell[]>([]);
  const [limit, setLimit] = useState<SalesLimitSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(DEFAULT_STATUS);

  // Online-sales pickup state. `pickupBusy` is the single guard that prevents
  // a second request while one is running. `returnSeconds` drives the
  // countdown back to the base screen after a successful pickup.
  const [pickupBusy, setPickupBusy] = useState(false);
  const [pickupStatus, setPickupStatus] = useState<Status | null>(null);
  const [pickupNextAction, setPickupNextAction] = useState<string | null>(null);
  const [returnSeconds, setReturnSeconds] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    const [cellsData, limitData] = await Promise.all([
      fetchCells(),
      fetchSalesLimit(),
    ]);
    setCells(cellsData);
    setLimit(limitData);
  }, []);

  useEffect(() => {
    // The online-sales mode does not display cells, so it must not query the
    // backend for them. The kiosk fetch behaviour is left unchanged.
    if (isOnlineSales) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    void (async () => {
      setLoading(true);
      setLoadError(null);
      try {
        await refresh();
      } catch {
        if (!cancelled) setLoadError(BACKEND_UNAVAILABLE);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refresh, isOnlineSales]);

  // Limit is set but fully spent: warn proactively and block selling so the
  // customer does not have to tap a cell to discover the limit is exhausted.
  const limitExhausted =
    limit !== null &&
    limit.status !== "NOT_SET" &&
    limit.remaining_amount_kopecks <= 0;

  const handleCellSelect = (cell: Cell) => {
    if (busy || limitExhausted) return;
    if (!isCellSellable(cell)) {
      setStatus({ severity: "error", text: CELL_NOT_SELLABLE_TEXT });
      return;
    }
    void handleSell(cell);
  };

  const handleSell = async (cell: Cell) => {
    if (busy || limitExhausted || !isCellSellable(cell)) return;
    setBusy(true);
    setStatus({ severity: "info", text: "Проверяем ячейку..." });
    await delay(350);
    setStatus({ severity: "info", text: "Открываем ячейку..." });
    try {
      const result = await sellFromCell(cell.number);
      if (result.success) {
        setStatus({ severity: "success", text: result.message });
      } else {
        setStatus({ severity: "error", text: result.message });
      }
      try {
        await refresh();
      } catch {
        /* keep the sale status; refresh is best-effort */
      }
    } catch (err) {
      setStatus({ severity: "error", text: toMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  // Countdown back to the base "Забрать товар" screen after a successful
  // pickup. When it reaches zero we clear the result and let the customer
  // start a new pickup.
  useEffect(() => {
    if (returnSeconds === null) return;
    if (returnSeconds <= 0) {
      setPickupStatus(null);
      setPickupNextAction(null);
      setReturnSeconds(null);
      return;
    }
    const timer = setTimeout(() => {
      setReturnSeconds((current) => (current === null ? null : current - 1));
    }, 1000);
    return () => clearTimeout(timer);
  }, [returnSeconds]);

  const applyPickupResult = (result: OnlineSalesPickupResponse) => {
    setPickupNextAction(result.next_action ?? null);

    if (result.code === ONLINE_SALES_CLOUD_UNAVAILABLE) {
      setPickupStatus({ severity: "error", text: CLOUD_UNAVAILABLE_TEXT });
      return;
    }
    if (result.success) {
      setPickupStatus({
        severity: "success",
        text: buildPickupSuccessText(result),
      });
      setReturnSeconds(RETURN_TO_BASE_SECONDS);
      return;
    }
    setPickupStatus({ severity: "error", text: result.message });
  };

  const handlePickup = async () => {
    // A second tap while a pickup is running must not start a second request.
    if (pickupBusy) return;
    setPickupBusy(true);
    setReturnSeconds(null);
    setPickupNextAction(null);
    setPickupStatus({
      severity: "info",
      text: "Проверяем оплаченные товары...",
    });
    await delay(350);
    setPickupStatus({ severity: "info", text: "Открываем ячейки..." });
    try {
      const result = await pickupOnlineSale();
      applyPickupResult(result);
    } catch (err) {
      setPickupStatus({ severity: "error", text: toMessage(err) });
      setPickupNextAction(null);
    } finally {
      setPickupBusy(false);
    }
  };

  return (
    <Box
      sx={[
        kioskRootSx,
        { minHeight: "100vh", display: "flex", flexDirection: "column" },
      ]}
    >
      <Container
        maxWidth="xl"
        sx={{
          flex: 1,
          pt: { xs: 1, md: 1.5 },
          pb: { xs: 2, md: 3 },
        }}
      >
        <Box sx={[glassPanelSx, { bgcolor: "rgba(255, 255, 255, 0.5)" }]}>
          {isOnlineSales ? (
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                gap: 3,
                minHeight: { xs: "50vh", md: "60vh" },
                py: 6,
              }}
            >
              {pickupStatus !== null && (
                <Box sx={{ width: "100%", maxWidth: 720 }}>
                  <Alert severity={pickupStatus.severity} sx={{ fontSize: "1.2rem" }}>
                    {pickupStatus.text}
                  </Alert>
                  {pickupNextAction !== null && (
                    <Typography
                      sx={{
                        mt: 1.5,
                        textAlign: "center",
                        fontSize: "1.05rem",
                        fontWeight: 600,
                        color: "rgba(28, 47, 66, 0.75)",
                      }}
                    >
                      {pickupNextAction}
                    </Typography>
                  )}
                  {returnSeconds !== null && returnSeconds > 0 && (
                    <Typography
                      sx={{
                        mt: 1,
                        textAlign: "center",
                        fontSize: "0.95rem",
                        color: "rgba(28, 47, 66, 0.6)",
                      }}
                    >
                      Возврат к началу через {returnSeconds} сек.
                    </Typography>
                  )}
                </Box>
              )}

              <Button
                variant="contained"
                color="error"
                onClick={() => void handlePickup()}
                disabled={pickupBusy || returnSeconds !== null}
                startIcon={
                  pickupBusy ? (
                    <CircularProgress size={28} color="inherit" />
                  ) : undefined
                }
                disableElevation
                sx={{
                  maxWidth: 720,
                  px: { xs: 4, md: 7 },
                  py: { xs: 3, md: 4 },
                  fontSize: { xs: "1.5rem", md: "2.1rem" },
                  fontWeight: 800,
                  lineHeight: 1.2,
                  textTransform: "none",
                  textAlign: "center",
                  borderRadius: "24px",
                  boxShadow: "0 16px 40px rgba(198, 40, 40, 0.4)",
                  "&:hover": {
                    boxShadow: "0 20px 48px rgba(198, 40, 40, 0.5)",
                  },
                }}
              >
                Забрать товар
              </Button>
            </Box>
          ) : (
            <>
          <Alert
            severity={limitExhausted ? "error" : status.severity}
            sx={{ mb: 2, fontSize: "1.1rem" }}
          >
            {limitExhausted ? LIMIT_EXHAUSTED_TEXT : status.text}
          </Alert>

          {loadError !== null && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {loadError}
            </Alert>
          )}

          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
              <CircularProgress />
            </Box>
          ) : (
            <>
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
                disabled={busy || limitExhausted}
                onSelect={handleCellSelect}
              />
            </>
          )}
            </>
          )}
        </Box>
      </Container>

      <Box
        component="footer"
        sx={{
          flexShrink: 0,
          px: { xs: 2, md: 3 },
          py: 2,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
          alignItems: "stretch",
          maxWidth: 360,
          ml: "auto",
          mr: { xs: 2, md: 3 },
          mb: { xs: 2, md: 3 },
        }}
      >
        <Button
          startIcon={<AdminPanelSettingsIcon />}
          onClick={onAdminMode}
          disableElevation
          sx={glassButtonSx}
        >
          Панель управления
        </Button>
        <Button
          startIcon={<EngineeringIcon />}
          onClick={onCourierMode}
          disableElevation
          sx={glassButtonSx}
        >
          Режим курьера
        </Button>
      </Box>
    </Box>
  );
}
