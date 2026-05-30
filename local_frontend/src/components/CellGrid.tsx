import Box from "@mui/material/Box";
import type { Cell } from "../types/cell";
import { CellCard } from "./CellCard";

interface CellGridProps {
  cells: Cell[];
  disabled: boolean;
  onSelect: (cell: Cell) => void;
}

export function CellGrid({ cells, disabled, onSelect }: CellGridProps) {
  return (
    <Box
      sx={{
        display: "grid",
        width: "100%",
        gap: { xs: 1.5, sm: 2 },
        gridTemplateColumns: {
          xs: "repeat(2, 1fr)",
          sm: "repeat(4, 1fr)",
          md: "repeat(6, 1fr)",
        },
      }}
    >
      {cells.map((cell) => (
        <CellCard
          key={cell.number}
          cell={cell}
          disabled={disabled}
          onSelect={onSelect}
        />
      ))}
    </Box>
  );
}
