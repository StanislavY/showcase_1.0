import { useEffect, useState, type ReactNode } from "react";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import CssBaseline from "@mui/material/CssBaseline";
import Typography from "@mui/material/Typography";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import { checkCourierSession } from "./api/authApi";
import { AdminLoginDialog } from "./components/AdminLoginDialog";
import { AdminPanelScreen } from "./components/AdminPanelScreen";
import { CourierLoginDialog } from "./components/CourierLoginDialog";
import { CourierScreen } from "./components/CourierScreen";
import { StartIssueScreen } from "./components/StartIssueScreen";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1976d2" },
    background: { default: "#f3f6fb" },
  },
  shape: { borderRadius: 12 },
});

const COURIER_TOKEN_KEY = "courier_session_token";
const ADMIN_TOKEN_KEY = "admin_session_token";

type AppMode = "issue" | "courier" | "admin";

export default function App() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [mode, setMode] = useState<AppMode>("issue");
  const [courierId, setCourierId] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [courierLoginOpen, setCourierLoginOpen] = useState(false);
  const [adminLoginOpen, setAdminLoginOpen] = useState(false);

  // On startup, only a courier session is auto-restored. The admin panel
  // never opens automatically after a reload — it requires pressing the
  // button and re-entering the password.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const courierToken = sessionStorage.getItem(COURIER_TOKEN_KEY);
      if (courierToken && (await checkCourierSession(courierToken))) {
        if (!cancelled) {
          setCourierId("");
          setMode("courier");
          setCheckingSession(false);
        }
        return;
      }
      sessionStorage.removeItem(COURIER_TOKEN_KEY);

      if (!cancelled) {
        setMode("issue");
        setCheckingSession(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCourierLoginSuccess = (token: string, id: string) => {
    sessionStorage.setItem(COURIER_TOKEN_KEY, token);
    setCourierId(id);
    setMode("courier");
    setCourierLoginOpen(false);
  };

  const handleAdminLoginSuccess = (token: string) => {
    sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
    setAdminToken(token);
    setMode("admin");
    setAdminLoginOpen(false);
  };

  const handleCourierLogout = () => {
    sessionStorage.removeItem(COURIER_TOKEN_KEY);
    setCourierId(null);
    setMode("issue");
  };

  // Leave the panel but keep the admin token for the rest of the session.
  const handleAdminBack = () => {
    setMode("issue");
  };

  // Full sign-out: drop the admin token before returning to the start screen.
  const handleAdminLogout = () => {
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    setAdminToken(null);
    setMode("issue");
  };

  let content: ReactNode;
  if (checkingSession) {
    content = (
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
    );
  } else if (mode === "courier") {
    content = (
      <CourierScreen
        courierId={courierId ?? ""}
        onLogout={handleCourierLogout}
      />
    );
  } else if (mode === "admin" && adminToken !== null) {
    content = (
      <AdminPanelScreen
        adminToken={adminToken}
        onBack={handleAdminBack}
        onLogout={handleAdminLogout}
      />
    );
  } else {
    content = (
      <>
        <StartIssueScreen
          onCourierMode={() => setCourierLoginOpen(true)}
          onAdminMode={() => setAdminLoginOpen(true)}
        />
        <CourierLoginDialog
          open={courierLoginOpen}
          onClose={() => setCourierLoginOpen(false)}
          onSuccess={handleCourierLoginSuccess}
        />
        <AdminLoginDialog
          open={adminLoginOpen}
          onClose={() => setAdminLoginOpen(false)}
          onSuccess={(token) => handleAdminLoginSuccess(token)}
        />
      </>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {content}
    </ThemeProvider>
  );
}
