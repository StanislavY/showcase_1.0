import Box from "@mui/material/Box";
import type { Cell } from "../types/cell";
import { CellCard } from "./CellCard";

interface CellGridProps {
  cells: Cell[];
  disabled?: boolean;
  onSelect?: (cell: Cell) => void;
  isCellSelectable?: (cell: Cell) => boolean;
}

export function CellGrid({
  cells,
  disabled = false,
  onSelect,
  isCellSelectable,
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
      {cells.map((cell) => {
        const selectable =
          onSelect !== undefined &&
          (isCellSelectable === undefined || isCellSelectable(cell));

        return (
          <CellCard
            key={cell.number}
            cell={cell}
            disabled={disabled}
            onSelect={selectable ? onSelect : undefined}
          />
        );
      })}
    </Box>
  );
}
