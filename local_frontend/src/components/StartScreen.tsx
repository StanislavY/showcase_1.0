import { useCallback, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Snackbar from "@mui/material/Snackbar";
import Typography from "@mui/material/Typography";
import EngineeringIcon from "@mui/icons-material/Engineering";
import { fetchCells, openCell } from "../api/cellsApi";
import { ApiError } from "../api/client";
import { CellGrid } from "./CellGrid";
import type { Cell } from "../types/cell";

interface StartScreenProps {
  onCourierMode: () => void;
}

type Feedback = { severity: "success" | "error"; text: string };

function toMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Неизвестная ошибка. Повторите попытку.";
}

export function StartScreen({ onCourierMode }: StartScreenProps) {
  const [cells, setCells] = useState<Cell[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const loadCells = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setCells(await fetchCells());
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadCells();
  }, [loadCells]);

  const handleOpen = async (cell: Cell) => {
    if (busy) return;
    setBusy(true);
    try {
      const result = await openCell(cell.number);
      setFeedback({ severity: "success", text: result.message });
    } catch (err) {
      setFeedback({ severity: "error", text: toMessage(err) });
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
      }}
    >
      <Box
        component="header"
        sx={{
          py: { xs: 2, md: 3 },
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
          Нажмите на ячейку, чтобы открыть
        </Typography>
      </Box>

      <Container maxWidth="xl" sx={{ py: { xs: 2, md: 4 } }}>
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
          <CellGrid
            cells={cells}
            disabled={busy}
            onSelect={(cell) => void handleOpen(cell)}
          />
        )}
      </Container>

      <Button
        variant="contained"
        color="secondary"
        startIcon={<EngineeringIcon />}
        onClick={onCourierMode}
        sx={{
          position: "fixed",
          right: 24,
          bottom: 24,
          zIndex: 1000,
          py: 1.75,
          px: 3,
          fontSize: "1.05rem",
          borderRadius: 999,
          boxShadow: 6,
        }}
      >
        Режим курьера
      </Button>

      <Snackbar
        open={feedback !== null}
        autoHideDuration={4000}
        onClose={() => setFeedback(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        {feedback !== null ? (
          <Alert
            severity={feedback.severity}
            onClose={() => setFeedback(null)}
            sx={{ width: "100%" }}
          >
            {feedback.text}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  );
}
