import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import type { Cell } from "../types/cell";
import {
  CELL_STATUS_COLOR,
  CELL_STATUS_LABEL,
  LOCK_STATUS_COLOR,
  LOCK_STATUS_LABEL,
} from "../labels";

interface CellCardProps {
  cell: Cell;
  disabled: boolean;
  onSelect: (cell: Cell) => void;
}

export function CellCard({ cell, disabled, onSelect }: CellCardProps) {
  return (
    <Card
      elevation={3}
      sx={{
        borderRadius: 3,
        aspectRatio: "1 / 1",
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <CardActionArea
        disabled={disabled}
        onClick={() => onSelect(cell)}
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
          sx={{ color: "text.secondary", lineHeight: 1, letterSpacing: 1 }}
        >
          ЯЧЕЙКА
        </Typography>
        <Typography
          variant="h3"
          sx={{ fontWeight: 700, lineHeight: 1, color: "primary.main" }}
        >
          {cell.number}
        </Typography>

        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            maxWidth: "100%",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {cell.product_name ?? "—"}
        </Typography>

        <Stack spacing={0.5} alignItems="center" sx={{ width: "100%" }}>
          <Chip
            size="small"
            label={CELL_STATUS_LABEL[cell.status]}
            color={CELL_STATUS_COLOR[cell.status]}
            variant="filled"
          />
          <Chip
            size="small"
            label={LOCK_STATUS_LABEL[cell.lock_status]}
            color={LOCK_STATUS_COLOR[cell.lock_status]}
            variant="outlined"
          />
        </Stack>
      </CardActionArea>
    </Card>
  );
}
