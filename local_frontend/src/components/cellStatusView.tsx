import type { SvgIconComponent } from "@mui/icons-material";
import LockIcon from "@mui/icons-material/Lock";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import type { Cell, CellStatus } from "../types/cell";

/**
 * Visual status used only for the courier screen redesign. It does NOT change
 * the backend cell status; it only buckets the existing statuses into the four
 * colour groups shown on the screen (зелёный / песочный / белый / красный).
 */
export type CellVisualStatus = "loaded" | "reserved" | "empty" | "error";

export interface CellStatusTone {
  /** Card background. */
  bg: string;
  /** Card border colour. */
  border: string;
  /** Border colour on hover / press. */
  borderActive: string;
  /** Cell number colour. */
  numberColor: string;
  /** Chip background. */
  chipBg: string;
  /** Chip text colour. */
  chipColor: string;
  /** Status icon colour. */
  iconColor: string;
  /** Legend dot colour. */
  dot: string;
}

export interface CellStatusView {
  status: CellVisualStatus;
  label: string;
  /** Compact label for the small status chip, e.g. "Готова". */
  shortLabel: string;
  icon: SvgIconComponent;
  tone: CellStatusTone;
}

export const CELL_STATUS_TONES: Record<CellVisualStatus, CellStatusTone> = {
  loaded: {
    bg: "rgba(198, 240, 215, 0.96)",
    border: "rgba(56, 160, 102, 0.75)",
    borderActive: "rgba(38, 120, 76, 1)",
    numberColor: "#15643c",
    chipBg: "rgba(46, 160, 95, 0.28)",
    chipColor: "#11643b",
    iconColor: "#1f9d57",
    dot: "#1faa54",
  },
  reserved: {
    bg: "rgba(250, 233, 198, 0.96)",
    border: "rgba(214, 158, 64, 0.75)",
    borderActive: "rgba(176, 122, 38, 1)",
    numberColor: "#8a5a12",
    chipBg: "rgba(212, 150, 50, 0.30)",
    chipColor: "#7d520f",
    iconColor: "#cf8f20",
    dot: "#e0a92e",
  },
  empty: {
    bg: "rgba(244, 247, 250, 0.97)",
    border: "rgba(150, 165, 182, 0.6)",
    borderActive: "rgba(104, 120, 138, 1)",
    numberColor: "#3c4855",
    chipBg: "rgba(110, 126, 144, 0.2)",
    chipColor: "#4a5562",
    iconColor: "#76859a",
    dot: "#cfd8e0",
  },
  error: {
    bg: "rgba(252, 215, 217, 0.96)",
    border: "rgba(220, 80, 88, 0.75)",
    borderActive: "rgba(186, 42, 50, 1)",
    numberColor: "#9c2229",
    chipBg: "rgba(214, 60, 68, 0.26)",
    chipColor: "#962027",
    iconColor: "#d83a42",
    dot: "#e23b43",
  },
};

interface VisualMapEntry {
  status: CellVisualStatus;
  label: string;
  shortLabel: string;
  icon: SvgIconComponent;
}

/**
 * Maps the backend cell status onto a visual bucket + Russian label + icon.
 * SERVICE is shown as "Зарезервирована" (the cell is occupied/held), BLOCKED
 * as "Недоступна", ERROR as "Ошибка".
 */
const STATUS_MAP: Record<CellStatus, VisualMapEntry> = {
  LOADED: {
    status: "loaded",
    label: "Заполнена, закрыта",
    shortLabel: "Готова",
    icon: LockIcon,
  },
  SERVICE: {
    status: "reserved",
    label: "Зарезервирована",
    shortLabel: "Резерв",
    icon: AccessTimeIcon,
  },
  EMPTY: {
    status: "empty",
    label: "Пусто",
    shortLabel: "Пусто",
    icon: Inventory2OutlinedIcon,
  },
  BLOCKED: {
    status: "error",
    label: "Недоступна",
    shortLabel: "Ошибка",
    icon: WarningAmberIcon,
  },
  ERROR: {
    status: "error",
    label: "Ошибка",
    shortLabel: "Ошибка",
    icon: WarningAmberIcon,
  },
};

export function getCellStatusView(cell: Cell): CellStatusView {
  const entry = STATUS_MAP[cell.status];
  return {
    status: entry.status,
    label: entry.label,
    shortLabel: entry.shortLabel,
    icon: entry.icon,
    tone: CELL_STATUS_TONES[entry.status],
  };
}

/** Legend rows, in display order. */
export const CELL_STATUS_LEGEND: {
  status: CellVisualStatus;
  label: string;
}[] = [
  { status: "loaded", label: "заполнена, закрыта" },
  { status: "reserved", label: "зарезервирована" },
  { status: "empty", label: "пусто" },
  { status: "error", label: "ошибка" },
];

/** Buckets a list of cells into visual-status counts for the summary panel. */
export function countByVisualStatus(
  cells: Cell[],
): Record<CellVisualStatus, number> {
  const counts: Record<CellVisualStatus, number> = {
    loaded: 0,
    reserved: 0,
    empty: 0,
    error: 0,
  };
  for (const cell of cells) {
    counts[STATUS_MAP[cell.status].status] += 1;
  }
  return counts;
}
