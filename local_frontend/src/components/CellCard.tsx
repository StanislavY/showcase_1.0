import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";

interface CellCardProps {
  cellId: number;
  onSelect: (cellId: number) => void;
}

export function CellCard({ cellId, onSelect }: CellCardProps) {
  return (
    <Card
      elevation={4}
      sx={{
        borderRadius: 3,
        height: "100%",
        transition: "transform 120ms ease, box-shadow 120ms ease",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: 8,
        },
      }}
    >
      <CardActionArea
        onClick={() => onSelect(cellId)}
        sx={{
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: { xs: 96, sm: 120, md: 140 },
          background:
            "linear-gradient(135deg, rgba(25,118,210,0.10) 0%, rgba(25,118,210,0.02) 100%)",
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 0.5,
          }}
        >
          <Typography
            variant="overline"
            sx={{ color: "text.secondary", lineHeight: 1 }}
          >
            ячейка
          </Typography>
          <Typography
            variant="h3"
            sx={{
              fontWeight: 700,
              color: "primary.main",
              lineHeight: 1,
              userSelect: "none",
            }}
          >
            {cellId}
          </Typography>
        </Box>
      </CardActionArea>
    </Card>
  );
}
