import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Typography from "@mui/material/Typography";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import LockOpenOutlinedIcon from "@mui/icons-material/LockOpenOutlined";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import type { SvgIconComponent } from "@mui/icons-material";
import type { Cell, LockStatus } from "../types/cell";
import { getCellStatusView } from "./cellStatusView";

interface CellCardProps {
  cell: Cell;
  disabled?: boolean;
  onClick?: () => void;
  onSelect?: (cell: Cell) => void;
}

/** Feminine lock labels ("ячейка закрыта") shown on the small lock chip. */
const LOCK_VIEW: Record<LockStatus, { label: string; icon: SvgIconComponent }> =
  {
    CLOSED: { label: "Закрыта", icon: LockOutlinedIcon },
    OPEN: { label: "Открыта", icon: LockOpenOutlinedIcon },
    UNKNOWN: { label: "Неизвестно", icon: HelpOutlineIcon },
    ERROR: { label: "Ошибка", icon: HelpOutlineIcon },
  };

interface CardChipProps {
  label: string;
  icon: SvgIconComponent;
  bg: string;
  color: string;
  border: string;
}

function CardChip({ label, icon: Icon, bg, color, border }: CardChipProps) {
  return (
    <Box
      sx={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "flex-start",
        gap: 0.4,
        px: 0.75,
        py: 0.25,
        borderRadius: 999,
        bgcolor: bg,
        border: "1px solid",
        borderColor: border,
        maxWidth: "100%",
      }}
    >
      <Icon sx={{ fontSize: 13, color, flexShrink: 0 }} />
      <Typography
        component="span"
        sx={{
          fontSize: "0.68rem",
          fontWeight: 700,
          lineHeight: 1.15,
          color,
          textAlign: "left",
          overflowWrap: "anywhere",
        }}
      >
        {label}
      </Typography>
    </Box>
  );
}

export function CellCard({
  cell,
  disabled = false,
  onClick,
  onSelect,
}: CellCardProps) {
  const view = getCellStatusView(cell);
  const { tone } = view;
  const StatusIcon = view.icon;
  const lock = LOCK_VIEW[cell.lock_status];

  const hasProduct = !!cell.product_name && cell.product_name.trim() !== "";
  const productText = hasProduct ? cell.product_name : "Ячейка свободна";

  const hasHandler = onClick !== undefined || onSelect !== undefined;
  const interactive = hasHandler && !disabled;

  const handleClick = () => {
    if (disabled) return;
    if (onClick !== undefined) onClick();
    else if (onSelect !== undefined) onSelect(cell);
  };

  const cardInner = (
      <Box
        className="cell-card"
        sx={{
          minHeight: 124,
          display: "flex",
          flexDirection: "column",
          p: 1.5,
          borderRadius: "16px",
          bgcolor: tone.bg,
          border: "1px solid",
          borderColor: tone.border,
          boxShadow: "0 4px 12px rgba(15, 50, 70, 0.1)",
          cursor: interactive ? "pointer" : "default",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 0.75,
          }}
        >
          <Typography
            component="span"
            sx={{
              fontWeight: 800,
              fontSize: "1.25rem",
              lineHeight: 1.1,
              color: tone.numberColor,
            }}
          >
            #{cell.number}
          </Typography>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-end",
              gap: 0.4,
              minWidth: 0,
            }}
          >
            <CardChip
              label={view.shortLabel}
              icon={StatusIcon}
              bg={tone.chipBg}
              color={tone.chipColor}
              border={tone.border}
            />
            <CardChip
              label={lock.label}
              icon={lock.icon}
              bg="rgba(255, 255, 255, 0.6)"
              color="rgba(45, 60, 72, 0.85)"
              border="rgba(120, 134, 150, 0.4)"
            />
          </Box>
        </Box>

        <Box
          sx={{
            flexGrow: 1,
            mt: 1,
            display: "flex",
            alignItems: "flex-start",
            gap: 0.6,
            minWidth: 0,
          }}
        >
          <Inventory2OutlinedIcon
            sx={{ fontSize: 17, color: tone.iconColor, mt: "1px", flexShrink: 0 }}
          />
          <Typography
            sx={{
              fontSize: "0.9rem",
              fontWeight: hasProduct ? 700 : 600,
              lineHeight: 1.2,
              color: hasProduct
                ? "rgba(28, 42, 54, 0.92)"
                : "rgba(28, 42, 54, 0.6)",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              wordBreak: "break-word",
            }}
          >
            {productText}
          </Typography>
        </Box>
      </Box>
  );

  if (!hasHandler) {
    return (
      <Box
        sx={{
          display: "block",
          width: "100%",
          borderRadius: "16px",
          opacity: disabled ? 0.55 : 1,
          "& .cell-card": { height: "100%" },
        }}
      >
        {cardInner}
      </Box>
    );
  }

  return (
    <ButtonBase
      disabled={disabled}
      onClick={handleClick}
      aria-disabled={disabled || undefined}
      focusRipple
      sx={{
        display: "block",
        width: "100%",
        textAlign: "left",
        borderRadius: "16px",
        opacity: disabled ? 0.55 : 1,
        transition:
          "transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease",
        "& .cell-card": { height: "100%" },
        ...(!disabled && {
          "@media (hover: hover)": {
            "&:hover .cell-card": {
              transform: "translateY(-2px)",
              boxShadow: "0 10px 22px rgba(15, 50, 70, 0.18)",
              borderColor: tone.borderActive,
            },
          },
          "&:active .cell-card": {
            transform: "translateY(-1px)",
            boxShadow: "0 6px 14px rgba(15, 50, 70, 0.2)",
            borderColor: tone.borderActive,
          },
        }),
      }}
    >
      {cardInner}
    </ButtonBase>
  );
}
