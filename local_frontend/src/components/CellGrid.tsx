import Box from "@mui/material/Box";
import type { SxProps, Theme } from "@mui/material/styles";
import type { Cell } from "../types/cell";
import { CellCard } from "./CellCard";

export interface CellGridColumns {
  xs?: number;
  sm?: number;
  md?: number;
}

const COURIER_GRID_COLUMNS: CellGridColumns = { xs: 2, sm: 4, md: 6 };
const ISSUE_GRID_COLUMNS: CellGridColumns = { xs: 2, sm: 5, md: 5 };

function columnsToTemplate(columns: CellGridColumns): SxProps<Theme> {
  const { xs = 2, sm = xs, md = sm } = columns;
  return {
    gridTemplateColumns: {
      xs: `repeat(${xs}, minmax(0, 1fr))`,
      sm: `repeat(${sm}, minmax(0, 1fr))`,
      md: `repeat(${md}, minmax(0, 1fr))`,
    },
  };
}

interface CellGridProps {
  cells: Cell[];
  disabled?: boolean;
  onSelect?: (cell: Cell) => void;
  /** Per-cell disabled state merged with the grid-level ``disabled`` flag. */
  isCellDisabled?: (cell: Cell) => boolean;
  showStatusChips?: boolean;
  columns?: CellGridColumns;
}

export function CellGrid({
  cells,
  disabled = false,
  onSelect,
  isCellDisabled,
  showStatusChips = false,
  columns,
}: CellGridProps) {
  const gridColumns = columns ?? (showStatusChips ? COURIER_GRID_COLUMNS : ISSUE_GRID_COLUMNS);

  return (
    <Box
      sx={{
        display: "grid",
        width: "100%",
        gap: { xs: 1.5, sm: 2 },
        alignItems: "stretch",
        ...columnsToTemplate(gridColumns),
      }}
    >
      {cells.map((cell) => (
        <CellCard
          key={cell.number}
          cell={cell}
          disabled={disabled || (isCellDisabled?.(cell) ?? false)}
          onSelect={onSelect}
          showStatusChips={showStatusChips}
        />
      ))}
    </Box>
  );
}
