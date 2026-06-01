import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Snackbar from "@mui/material/Snackbar";
import Typography from "@mui/material/Typography";
import EngineeringIcon from "@mui/icons-material/Engineering";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import { fetchCells } from "../api/cellsApi";
import { fetchSalesLimit, sellFromCell } from "../api/salesApi";
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
import type { TerminalMode } from "../settings/terminalMode";

interface StartIssueScreenProps {
  terminalMode: TerminalMode;
  onCourierMode: () => void;
  onAdminMode: () => void;
}

const ONLINE_SALES_PLACEHOLDER =
  "Режим онлайн-продаж будет реализован следующим этапом";

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
  const [onlineSalesNotice, setOnlineSalesNotice] = useState(false);

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
                justifyContent: "center",
                alignItems: "center",
                minHeight: { xs: "50vh", md: "60vh" },
                py: 6,
              }}
            >
              <Button
                variant="contained"
                color="error"
                onClick={() => setOnlineSalesNotice(true)}
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
                Отсканируйте QR код товара для покупки
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

      <Snackbar
        open={onlineSalesNotice}
        autoHideDuration={4000}
        onClose={() => setOnlineSalesNotice(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          severity="info"
          onClose={() => setOnlineSalesNotice(false)}
          sx={{ width: "100%" }}
        >
          {ONLINE_SALES_PLACEHOLDER}
        </Alert>
      </Snackbar>
    </Box>
  );
}
