import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

interface StatusMessageProps {
  message: string;
}

export function StatusMessage({ message }: StatusMessageProps) {
  return (
    <Paper
      elevation={2}
      sx={{
        py: 2,
        px: 3,
        borderRadius: 3,
        textAlign: "center",
        bgcolor: "background.paper",
        minHeight: 64,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Typography variant="h6" sx={{ color: "text.secondary" }}>
        {message || "Ожидание действия..."}
      </Typography>
    </Paper>
  );
}
