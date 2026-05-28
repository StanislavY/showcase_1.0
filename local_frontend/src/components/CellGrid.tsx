import Box from "@mui/material/Box";
import type { Cell } from "../types/cell";
import { CellCard } from "./CellCard";

interface CellGridProps {
  cells: Cell[];
  onSelect: (cellId: number) => void;
}

export function CellGrid({ cells, onSelect }: CellGridProps) {
  return (
    <Box
      sx={{
        display: "grid",
        width: "100%",
        gap: { xs: 1.5, sm: 2, md: 2.5 },
        gridTemplateColumns: {
          xs: "repeat(3, 1fr)",
          sm: "repeat(5, 1fr)",
          md: "repeat(9, 1fr)",
        },
      }}
    >
      {cells.map((cell) => (
        <CellCard key={cell.id} cellId={cell.id} onSelect={onSelect} />
      ))}
    </Box>
  );
}
