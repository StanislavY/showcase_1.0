import Box from "@mui/material/Box";
import type { Cell } from "../types/cell";
import { CellCard } from "./CellCard";

interface CellGridProps {
  cells: Cell[];
  disabled?: boolean;
  onSelect?: (cell: Cell) => void;
  /** Per-cell disabled state merged with the grid-level ``disabled`` flag. */
  isCellDisabled?: (cell: Cell) => boolean;
}

export function CellGrid({
  cells,
  disabled = false,
  onSelect,
  isCellDisabled,
}: CellGridProps) {
  return (
    <Box
      sx={{
        display: "grid",
        width: "100%",
        gap: { xs: 1.5, sm: 2 },
        gridTemplateColumns: {
          xs: "repeat(2, minmax(0, 1fr))",
          sm: "repeat(4, minmax(0, 1fr))",
          md: "repeat(6, minmax(0, 1fr))",
        },
      }}
    >
      {cells.map((cell) => (
        <CellCard
          key={cell.number}
          cell={cell}
          disabled={disabled || (isCellDisabled?.(cell) ?? false)}
          onSelect={onSelect}
        />
      ))}
    </Box>
  );
}
