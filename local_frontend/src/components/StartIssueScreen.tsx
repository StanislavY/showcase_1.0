import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import EngineeringIcon from "@mui/icons-material/Engineering";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import { fetchCells } from "../api/cellsApi";
import { fetchSalesLimit, sellFromCell } from "../api/salesApi";
import { ApiError } from "../api/client";
import { kopecksToRublesText } from "../utils/money";
import type { Cell } from "../types/cell";
import type { SalesLimitSummary } from "../types/sales";

interface StartIssueScreenProps {
  onCourierMode: () => void;
  onAdminMode: () => void;
}

type Status = { severity: "info" | "success" | "error"; text: string };

const DEFAULT_STATUS: Status = {
  severity: "info",
  text: "Выберите ячейку с товаром",
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
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default",
        touchAction: "manipulation",
        pb: 14,
      }}
    >
      <Box
        component="header"
        sx={{
          py: { xs: 2, md: 3 },
          px: { xs: 2, md: 3 },
          textAlign: "center",
          bgcolor: "primary.main",
          color: "primary.contrastText",
          boxShadow: 2,
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Постамат
        </Typography>
        <Typography variant="subtitle1" sx={{ opacity: 0.9 }}>
          Нажмите на ячейку с товаром, чтобы забрать заказ
        </Typography>
        {limit !== null && limit.status !== "NOT_SET" && (
          <Typography variant="h6" sx={{ mt: 0.5, fontWeight: 600 }}>
            Остаток лимита:{" "}
            {kopecksToRublesText(limit.remaining_amount_kopecks)}
          </Typography>
        )}
      </Box>

      <Container maxWidth="xl" sx={{ py: { xs: 2, md: 4 } }}>
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
              return (
                <Card
                  key={cell.number}
                  elevation={3}
                  sx={{
                    borderRadius: 3,
                    aspectRatio: "1 / 1",
                    opacity: busy || limitExhausted ? 0.5 : 1,
                  }}
                >
                  <CardActionArea
                    disabled={busy || limitExhausted}
                    onClick={() => void handleSell(cell)}
                    sx={{
                      height: "100%",
                      p: 1,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 0.5,
                      textAlign: "center",
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                        lineHeight: 1,
                        letterSpacing: 1,
                      }}
                    >
                      ЯЧЕЙКА
                    </Typography>
                    <Typography
                      variant="h3"
                      sx={{
                        fontWeight: 700,
                        lineHeight: 1,
                        color: "primary.main",
                      }}
                    >
                      {cell.number}
                    </Typography>
                    {hasProduct ? (
                      <Stack spacing={0.25} sx={{ width: "100%" }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
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
                          sx={{ fontWeight: 700, color: "success.main" }}
                        >
                          {formatPrice(cell.product_price as number)}
                        </Typography>
                      </Stack>
                    ) : (
                      <Typography
                        variant="body2"
                        sx={{ color: "text.disabled", fontWeight: 600 }}
                      >
                        Пусто
                      </Typography>
                    )}
                  </CardActionArea>
                </Card>
              );
            })}
          </Box>
        )}
      </Container>

      <Box
        sx={{
          position: "fixed",
          right: 24,
          bottom: 24,
          zIndex: 1000,
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
          alignItems: "stretch",
        }}
      >
        <Button
          variant="outlined"
          color="primary"
          startIcon={<AdminPanelSettingsIcon />}
          onClick={onAdminMode}
          sx={{
            py: 1.75,
            px: 3,
            fontSize: "1.05rem",
            borderRadius: 999,
            boxShadow: 4,
            bgcolor: "background.paper",
          }}
        >
          Панель управления
        </Button>
        <Button
          variant="contained"
          color="secondary"
          startIcon={<EngineeringIcon />}
          onClick={onCourierMode}
          sx={{
            py: 1.75,
            px: 3,
            fontSize: "1.05rem",
            borderRadius: 999,
            boxShadow: 6,
          }}
        >
          Режим курьера
        </Button>
      </Box>
    </Box>
  );
}
