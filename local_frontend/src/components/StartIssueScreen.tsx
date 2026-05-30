import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import EngineeringIcon from "@mui/icons-material/Engineering";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import { fetchCells } from "../api/cellsApi";
import { fetchSalesLimit, sellFromCell } from "../api/salesApi";
import { ApiError } from "../api/client";
import { getCellStatusView } from "./cellStatusView";
import {
  glassButtonSx,
  glassPanelSx,
  kioskRootSx,
} from "./kioskScreenStyles";
import type { Cell } from "../types/cell";
import type { SalesLimitSummary } from "../types/sales";

interface StartIssueScreenProps {
  onCourierMode: () => void;
  onAdminMode: () => void;
}

type Status = { severity: "info" | "success" | "error"; text: string };

const DEFAULT_STATUS: Status = {
  severity: "info",
  text: "Нажмите на номер ячейки, чтобы купить",
};

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

/** Price is stored in roubles on the backend; show it with two decimals. */
function formatPrice(price: number): string {
  return (
    price.toLocaleString("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }) + " ₽"
  );
}

export function StartIssueScreen({
  onCourierMode,
  onAdminMode,
}: StartIssueScreenProps) {
  const [cells, setCells] = useState<Cell[]>([]);
  const [limit, setLimit] = useState<SalesLimitSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>(DEFAULT_STATUS);

  const refresh = useCallback(async () => {
    const [cellsData, limitData] = await Promise.all([
      fetchCells(),
      fetchSalesLimit(),
    ]);
    setCells(cellsData);
    setLimit(limitData);
  }, []);

  useEffect(() => {
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
  }, [refresh]);

  // Limit is set but fully spent: warn proactively and block selling so the
  // customer does not have to tap a cell to discover the limit is exhausted.
  const limitExhausted =
    limit !== null &&
    limit.status !== "NOT_SET" &&
    limit.remaining_amount_kopecks <= 0;

  const handleSell = async (cell: Cell) => {
    if (busy || limitExhausted) return;
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
            <Box
              sx={{
                display: "grid",
                width: "100%",
                gap: { xs: 1.5, sm: 2 },
                gridTemplateColumns: {
                  xs: "repeat(3, 1fr)",
                  sm: "repeat(5, 1fr)",
                  md: "repeat(6, 1fr)",
                },
              }}
            >
              {cells.map((cell) => {
                const hasProduct =
                  cell.status === "LOADED" &&
                  cell.product_name !== null &&
                  cell.product_price !== null;
                const { tone } = getCellStatusView(cell);
                return (
                  <ButtonBase
                    key={cell.number}
                    disabled={busy || limitExhausted}
                    onClick={() => void handleSell(cell)}
                    focusRipple
                    sx={{
                      display: "block",
                      width: "100%",
                      borderRadius: "16px",
                      opacity: busy || limitExhausted ? 0.5 : 1,
                      transition:
                        "transform 0.15s ease, box-shadow 0.15s ease",
                      "& .issue-cell": { height: "100%" },
                      "@media (hover: hover)": {
                        "&:hover .issue-cell": {
                          transform: "translateY(-2px)",
                          boxShadow: "0 10px 22px rgba(15, 50, 70, 0.18)",
                        },
                      },
                      "&:active .issue-cell": {
                        transform: "translateY(-1px)",
                      },
                    }}
                  >
                    <Box
                      className="issue-cell"
                      sx={{
                        aspectRatio: "1 / 1",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: 0.5,
                        p: 1,
                        textAlign: "center",
                        borderRadius: "16px",
                        bgcolor: tone.bg,
                        border: "1px solid",
                        borderColor: tone.border,
                        boxShadow: "0 4px 12px rgba(15, 50, 70, 0.1)",
                        overflow: "hidden",
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          color: tone.chipColor,
                          lineHeight: 1,
                          letterSpacing: 1,
                          fontWeight: 700,
                        }}
                      >
                        ЯЧЕЙКА
                      </Typography>
                      <Typography
                        variant="h3"
                        sx={{
                          fontWeight: 800,
                          lineHeight: 1,
                          color: tone.numberColor,
                        }}
                      >
                        {cell.number}
                      </Typography>
                      {hasProduct ? (
                        <Stack spacing={0.25} sx={{ width: "100%" }}>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 700,
                              color: "rgba(28, 42, 54, 0.92)",
                              maxWidth: "100%",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {cell.product_name}
                          </Typography>
                          <Typography
                            variant="body1"
                            sx={{ fontWeight: 800, color: tone.numberColor }}
                          >
                            {formatPrice(cell.product_price as number)}
                          </Typography>
                        </Stack>
                      ) : (
                        <Typography
                          variant="body2"
                          sx={{ color: tone.chipColor, fontWeight: 600 }}
                        >
                          Пусто
                        </Typography>
                      )}
                    </Box>
                  </ButtonBase>
                );
              })}
            </Box>
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
