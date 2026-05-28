import { useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider, createTheme } from "@mui/material/styles";
import { CellGrid } from "./components/CellGrid";
import { StatusMessage } from "./components/StatusMessage";
import { createCells } from "./types/cell";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#1976d2" },
    background: { default: "#f3f6fb" },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily:
      "Roboto, 'Segoe UI', Arial, system-ui, -apple-system, sans-serif",
  },
});

export default function App() {
  const cells = useMemo(() => createCells(), []);
  const [message, setMessage] = useState<string>("");

  const handleSelect = (cellId: number) => {
    setMessage(`Вы выбрали ячейку №${cellId}`);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
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
          <Typography variant="h3" sx={{ fontWeight: 600 }}>
            Выберите ячейку
          </Typography>
        </Box>

        <Container
          maxWidth="xl"
          sx={{
            flexGrow: 1,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            py: { xs: 3, md: 5 },
          }}
        >
          <CellGrid cells={cells} onSelect={handleSelect} />
        </Container>

        <Box
          component="footer"
          sx={{
            px: { xs: 2, md: 4 },
            pb: { xs: 2, md: 3 },
          }}
        >
          <StatusMessage message={message} />
        </Box>
      </Box>
    </ThemeProvider>
  );
}
