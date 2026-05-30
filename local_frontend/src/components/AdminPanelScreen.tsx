import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Divider from "@mui/material/Divider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import LogoutIcon from "@mui/icons-material/Logout";
import BackspaceOutlinedIcon from "@mui/icons-material/BackspaceOutlined";
import { ApiError } from "../api/client";
import { fetchSalesLimit, setSalesLimit } from "../api/salesApi";
import { kopecksToRublesText, rublesInputToKopecks } from "../utils/money";
import type { SalesLimitSummary } from "../types/sales";

interface AdminPanelScreenProps {
  adminToken: string;
  onBack: () => void;
  onLogout: () => void;
}

type Feedback = { severity: "success" | "error" | "info"; text: string };

function toMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Неизвестная ошибка. Повторите попытку.";
}

const KEYPAD_ROWS: string[][] = [
  ["1", "2", "3"],
  ["4", "5", "6"],
  ["7", "8", "9"],
  ["clear", "0", "back"],
];

export function AdminPanelScreen({
  adminToken,
  onBack,
  onLogout,
}: AdminPanelScreenProps) {
  const [summary, setSummary] = useState<SalesLimitSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [rublesInput, setRublesInput] = useState("");

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSummary(await fetchSalesLimit());
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  const limitIsSet =
    summary !== null && summary.limit_id !== null && summary.status !== "NOT_SET";

  const handleKey = (key: string) => {
    if (busy) return;
    setFeedback(null);
    if (key === "clear") {
      setRublesInput("");
      return;
    }
    if (key === "back") {
      setRublesInput((prev) => prev.slice(0, -1));
      return;
    }
    setRublesInput((prev) => {
      // Drop leading zeros and cap length so the field stays readable.
      const next = (prev + key).replace(/^0+(?=\d)/, "");
      return next.length > 9 ? prev : next;
    });
  };

  const handleSetLimit = async () => {
    const kopecks = rublesInputToKopecks(rublesInput);
    if (kopecks <= 0) {
      setFeedback({ severity: "error", text: "Введите сумму лимита" });
      return;
    }
    setBusy(true);
    setFeedback(null);
    try {
      const updated = await setSalesLimit(kopecks, adminToken);
      setSummary(updated);
      setRublesInput("");
      setFeedback({ severity: "success", text: "Лимит установлен" });
    } catch (err) {
      setFeedback({ severity: "error", text: toMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  const enteredText =
    rublesInput === ""
      ? "0 ₽"
      : `${Number.parseInt(rublesInput, 10).toLocaleString("ru-RU")} ₽`;

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "background.default",
        touchAction: "manipulation",
      }}
    >
      <Box
        component="header"
        sx={{
          py: { xs: 2, md: 3 },
          px: { xs: 2, md: 3 },
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          bgcolor: "primary.main",
          color: "primary.contrastText",
          boxShadow: 2,
        }}
      >
        <Button
          variant="contained"
          color="inherit"
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          disabled={busy}
          sx={{
            flexShrink: 0,
            py: 1.25,
            px: 2.5,
            fontSize: "1rem",
            color: "primary.main",
            bgcolor: "primary.contrastText",
          }}
        >
          Назад
        </Button>
        <Typography variant="h4" sx={{ fontWeight: 600, textAlign: "center" }}>
          Панель управления
        </Typography>
        <Button
          variant="contained"
          color="inherit"
          startIcon={<LogoutIcon />}
          onClick={onLogout}
          disabled={busy}
          sx={{
            flexShrink: 0,
            py: 1.25,
            px: 2.5,
            fontSize: "1rem",
            color: "primary.main",
            bgcolor: "primary.contrastText",
          }}
        >
          Выйти
        </Button>
      </Box>

      <Container maxWidth="sm" sx={{ py: { xs: 2, md: 4 } }}>
        {error !== null && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Stack spacing={3}>
            <Card variant="outlined">
              <CardContent>
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    mb: 1.5,
                  }}
                >
                  <Typography variant="h6">Текущий лимит</Typography>
                  <Button onClick={() => void loadSummary()} disabled={busy}>
                    Обновить
                  </Button>
                </Box>
                <Divider sx={{ mb: 2 }} />
                {limitIsSet && summary !== null ? (
                  <Stack spacing={1.25}>
                    <Row
                      label="Установленный лимит"
                      value={kopecksToRublesText(summary.limit_amount_kopecks)}
                    />
                    <Row
                      label="Продано в рамках лимита"
                      value={kopecksToRublesText(summary.sold_amount_kopecks)}
                    />
                    <Row
                      label="Остаток лимита"
                      value={kopecksToRublesText(
                        summary.remaining_amount_kopecks,
                      )}
                      strong
                    />
                  </Stack>
                ) : (
                  <Typography color="text.secondary" sx={{ fontSize: "1.1rem" }}>
                    Лимит пока не установлен
                  </Typography>
                )}
              </CardContent>
            </Card>

            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Новый лимит
                </Typography>

                <Box
                  sx={{
                    mb: 2,
                    py: 2,
                    px: 2,
                    borderRadius: 2,
                    border: "2px solid",
                    borderColor: "primary.main",
                    bgcolor: "background.default",
                    textAlign: "center",
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: "2.6rem",
                      fontWeight: 700,
                      lineHeight: 1.1,
                      color: rublesInput === "" ? "text.disabled" : "text.primary",
                    }}
                  >
                    {enteredText}
                  </Typography>
                </Box>

                {feedback !== null && (
                  <Alert
                    severity={feedback.severity}
                    sx={{ mb: 2 }}
                    onClose={() => setFeedback(null)}
                  >
                    {feedback.text}
                  </Alert>
                )}

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: 1.5,
                    mb: 2,
                  }}
                >
                  {KEYPAD_ROWS.flat().map((key) => (
                    <Button
                      key={key}
                      variant={key === "0" || /\d/.test(key) ? "outlined" : "contained"}
                      color={key === "clear" ? "warning" : "primary"}
                      onClick={() => handleKey(key)}
                      disabled={busy}
                      sx={{
                        py: 2.5,
                        fontSize: "1.6rem",
                        fontWeight: 700,
                        minHeight: 72,
                      }}
                    >
                      {key === "clear" ? (
                        "Очистить"
                      ) : key === "back" ? (
                        <BackspaceOutlinedIcon fontSize="large" />
                      ) : (
                        key
                      )}
                    </Button>
                  ))}
                </Box>

                <Button
                  variant="contained"
                  onClick={() => void handleSetLimit()}
                  disabled={busy}
                  fullWidth
                  sx={{ py: 1.75, fontSize: "1.2rem", fontWeight: 700 }}
                  startIcon={
                    busy ? (
                      <CircularProgress size={22} color="inherit" />
                    ) : undefined
                  }
                >
                  Установить лимит
                </Button>
              </CardContent>
            </Card>
          </Stack>
        )}
      </Container>
    </Box>
  );
}

function Row({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <Box sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
      <Typography color="text.secondary">{label}</Typography>
      <Typography sx={{ fontWeight: strong ? 700 : 500 }}>{value}</Typography>
    </Box>
  );
}
