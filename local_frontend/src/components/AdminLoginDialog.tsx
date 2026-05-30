import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import TextField from "@mui/material/TextField";
import { loginAdmin } from "../api/adminAuthApi";

interface AdminLoginDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (token: string, adminId: string) => void;
}

const BIG_BUTTON = { py: 1.25, fontSize: "1.05rem" } as const;

export function AdminLoginDialog({
  open,
  onClose,
  onSuccess,
}: AdminLoginDialogProps) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Reset transient state every time the dialog is (re)opened.
  useEffect(() => {
    if (open) {
      setPassword("");
      setLoading(false);
      setErrorMessage(null);
    }
  }, [open]);

  const submit = async () => {
    if (loading || password.trim() === "") return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const result = await loginAdmin(password);
      if (result.success && result.token && result.admin_id) {
        onSuccess(result.token, result.admin_id);
      } else {
        setErrorMessage(result.message || "Неверный пароль администратора");
      }
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Локальный backend недоступен",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (loading) return;
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} fullWidth maxWidth="xs">
      <DialogTitle>Вход в панель управления</DialogTitle>
      <DialogContent dividers>
        {errorMessage !== null && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        <TextField
          label="Пароль администратора"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void submit();
            }
          }}
          fullWidth
          autoFocus
          disabled={loading}
          inputProps={{ inputMode: "numeric" }}
        />
      </DialogContent>
      <DialogActions sx={{ p: 2, gap: 1 }}>
        <Button onClick={handleClose} disabled={loading} sx={BIG_BUTTON}>
          Отмена
        </Button>
        <Button
          variant="contained"
          onClick={() => void submit()}
          disabled={loading || password.trim() === ""}
          sx={BIG_BUTTON}
          startIcon={
            loading ? <CircularProgress size={20} color="inherit" /> : undefined
          }
        >
          Войти
        </Button>
      </DialogActions>
    </Dialog>
  );
}
