import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import CssBaseline from "@mui/material/CssBaseline";
import Typography from "@mui/material/Typography";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import { checkCourierSession } from "./api/authApi";
import { CourierLoginDialog } from "./components/CourierLoginDialog";
import { CourierScreen } from "./components/CourierScreen";
import { StartScreen } from "./components/StartScreen";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1976d2" },
    background: { default: "#f3f6fb" },
  },
  shape: { borderRadius: 12 },
});

const SESSION_TOKEN_KEY = "courier_session_token";

type AppMode = "start" | "courier";

export default function App() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [mode, setMode] = useState<AppMode>("start");
  const [courierId, setCourierId] = useState<string | null>(null);
  const [loginOpen, setLoginOpen] = useState(false);

  // On startup, restore a courier session if the stored token is still valid.
  useEffect(() => {
    const token = sessionStorage.getItem(SESSION_TOKEN_KEY);
    if (!token) {
      setCheckingSession(false);
      return;
    }
    let cancelled = false;
    void (async () => {
      const valid = await checkCourierSession(token);
      if (cancelled) return;
      if (valid) {
        // The courier id is not persisted (only the token lives in
        // sessionStorage); the backend identifies the courier from the token.
        setCourierId("");
        setMode("courier");
      } else {
        sessionStorage.removeItem(SESSION_TOKEN_KEY);
        setMode("start");
      }
      setCheckingSession(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLoginSuccess = (token: string, id: string) => {
    sessionStorage.setItem(SESSION_TOKEN_KEY, token);
    setCourierId(id);
    setMode("courier");
    setLoginOpen(false);
  };

  const handleLogout = () => {
    sessionStorage.removeItem(SESSION_TOKEN_KEY);
    setCourierId(null);
    setMode("start");
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {checkingSession ? (
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 2,
            bgcolor: "background.default",
          }}
        >
          <CircularProgress />
          <Typography variant="h6" color="text.secondary">
            Проверяем сессию...
          </Typography>
        </Box>
      ) : mode === "courier" ? (
        <CourierScreen courierId={courierId ?? ""} onLogout={handleLogout} />
      ) : (
        <>
          <StartScreen onCourierMode={() => setLoginOpen(true)} />
          <CourierLoginDialog
            open={loginOpen}
            onClose={() => setLoginOpen(false)}
            onSuccess={handleLoginSuccess}
          />
        </>
      )}
    </ThemeProvider>
  );
}
