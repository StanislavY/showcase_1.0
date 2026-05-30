import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
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
import {
  glassButtonSx,
  glassCardSx,
  glassPanelSx,
  kioskHeaderSx,
  kioskRootSx,
  kioskTitleSx,
  KIOSK_TEXT,
} from "./kioskScreenStyles";
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
    <Box sx={kioskRootSx}>
      <Box component="header" sx={kioskHeaderSx}>
        <Button
          variant="contained"
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          disabled={busy}
          disableElevation
          sx={glassButtonSx}
        >
          Назад
        </Button>
        <Typography variant="h4" sx={[kioskTitleSx, { textAlign: "center" }]}>
          Панель управления
        </Typography>
        <Button
          variant="contained"
          startIcon={<LogoutIcon />}
          onClick={onLogout}
          disabled={busy}
          disableElevation
          sx={glassButtonSx}
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
            <Box sx={glassPanelSx}>
              <Box
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  mb: 1.5,
                }}
              >
                <Typography variant="h6" sx={{ fontWeight: 700, color: KIOSK_TEXT }}>
                  Текущий лимит
                </Typography>
                <Button
                  onClick={() => void loadSummary()}
                  disabled={busy}
                  disableElevation
                  sx={glassButtonSx}
                >
                  Обновить
                </Button>
              </Box>
              <Divider sx={{ mb: 2, borderColor: "rgba(180, 205, 200, 0.45)" }} />
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
                <Typography
                  sx={{ fontSize: "1.1rem", color: "rgba(28, 47, 66, 0.6)" }}
                >
                  Лимит пока не установлен
                </Typography>
              )}
            </Box>

            <Box sx={glassPanelSx}>
              <Typography
                variant="h6"
                sx={{ mb: 2, fontWeight: 700, color: KIOSK_TEXT }}
              >
                Новый лимит
              </Typography>

              <Box
                sx={[
                  glassCardSx,
                  {
                    mb: 2,
                    py: 2,
                    px: 2,
                    textAlign: "center",
                  },
                ]}
              >
                <Typography
                  sx={{
                    fontSize: "2.6rem",
                    fontWeight: 700,
                    lineHeight: 1.1,
                    color:
                      rublesInput === "" ? "rgba(28, 47, 66, 0.4)" : KIOSK_TEXT,
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
                    onClick={() => handleKey(key)}
                    disabled={busy}
                    disableElevation
                    sx={{
                      py: 2.5,
                      minHeight: 72,
                      fontSize: "1.6rem",
                      fontWeight: 700,
                      textTransform: "none",
                      color: key === "clear" ? "#9c2229" : KIOSK_TEXT,
                      bgcolor: "rgba(255, 255, 255, 0.92)",
                      borderRadius: "16px",
                      border: "1px solid rgba(180, 205, 200, 0.5)",
                      boxShadow: "0 6px 16px rgba(26, 47, 66, 0.08)",
                      "&:hover": {
                        bgcolor: "#ffffff",
                        boxShadow: "0 8px 20px rgba(26, 47, 66, 0.12)",
                      },
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
                disableElevation
                sx={{
                  py: 1.75,
                  fontSize: "1.2rem",
                  fontWeight: 700,
                  textTransform: "none",
                  color: KIOSK_TEXT,
                  bgcolor: "#c6f0d7",
                  borderRadius: "16px",
                  border: "1px solid rgba(56, 160, 102, 0.75)",
                  boxShadow: "0 8px 20px rgba(31, 170, 84, 0.22)",
                  "&:hover": {
                    bgcolor: "#b5e8cc",
                    boxShadow: "0 10px 24px rgba(31, 170, 84, 0.28)",
                  },
                }}
                startIcon={
                  busy ? (
                    <CircularProgress size={22} color="inherit" />
                  ) : undefined
                }
              >
                Установить лимит
              </Button>
            </Box>
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
      <Typography sx={{ color: "rgba(28, 47, 66, 0.6)" }}>{label}</Typography>
      <Typography sx={{ fontWeight: strong ? 700 : 500, color: KIOSK_TEXT }}>
        {value}
      </Typography>
    </Box>
  );
}
