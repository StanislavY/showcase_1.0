import type { Theme } from "@mui/material/styles";
import type { SystemStyleObject } from "@mui/system";

/**
 * Shared visual theme for the kiosk screens (courier, issue, admin).
 *
 * The look is a light, semi-transparent "glass" layer placed over the
 * `courier-bg.png` background image: white translucent panels, soft shadows,
 * large rounded corners, a calm dark text colour (#1c2f42) and a blue accent
 * (#1976d2). These objects only describe presentation; no business logic,
 * API calls or data types depend on them.
 */

/** Brand accent + text colours, kept in one place for reuse. */
export const KIOSK_ACCENT = "#1976d2";
export const KIOSK_TEXT = "#1c2f42";

/**
 * Page root: full-height surface that paints the fixed background image.
 * Screens may merge extra props (e.g. bottom padding) via `[kioskRootSx, ...]`.
 */
export const kioskRootSx: SystemStyleObject<Theme> = {
  minHeight: "100vh",
  touchAction: "manipulation",
  overflowX: "hidden",
  backgroundImage: 'url("/courier-bg.png")',
  backgroundSize: "cover",
  backgroundPosition: "center",
  backgroundRepeat: "no-repeat",
  backgroundAttachment: "fixed",
};

/** Transparent header bar (no solid blue MUI app-bar). */
export const kioskHeaderSx: SystemStyleObject<Theme> = {
  py: { xs: 1.75, md: 2.25 },
  px: { xs: 2, md: 4 },
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 2,
};

/** Large dark heading used in headers. */
export const kioskTitleSx: SystemStyleObject<Theme> = {
  fontWeight: 700,
  color: KIOSK_TEXT,
  letterSpacing: "-0.01em",
};

/** Calm dark secondary text (subtitles, remaining limit, etc.). */
export const kioskSubtitleSx: SystemStyleObject<Theme> = {
  color: "rgba(28, 47, 66, 0.6)",
};

/** White translucent glass panel with blur, soft shadow and big radius. */
export const glassPanelSx: SystemStyleObject<Theme> = {
  p: { xs: 2, md: 2.75 },
  borderRadius: "24px",
  bgcolor: "rgba(255, 255, 255, 0.82)",
  border: "1px solid rgba(180, 205, 200, 0.45)",
  boxShadow: "0 16px 40px rgba(26, 47, 66, 0.08)",
  backdropFilter: "blur(8px)",
};

/**
 * Glass button matching the courier "logout" button: white/translucent,
 * dark text, no uppercase, soft shadow and 16px corners.
 */
export const glassButtonSx: SystemStyleObject<Theme> = {
  flexShrink: 0,
  py: 1.25,
  px: 2.5,
  fontSize: "1rem",
  fontWeight: 600,
  textTransform: "none",
  color: KIOSK_TEXT,
  bgcolor: "rgba(255, 255, 255, 0.92)",
  borderRadius: "16px",
  border: "1px solid rgba(180, 205, 200, 0.5)",
  boxShadow: "0 8px 20px rgba(26, 47, 66, 0.1)",
  "&:hover": {
    bgcolor: "#ffffff",
    boxShadow: "0 10px 24px rgba(26, 47, 66, 0.14)",
  },
};

/**
 * Smaller white translucent surface used for cards / sub-blocks (e.g. the
 * entered-amount field or info cards). Slightly more opaque than the panel.
 */
export const glassCardSx: SystemStyleObject<Theme> = {
  borderRadius: "16px",
  bgcolor: "rgba(255, 255, 255, 0.9)",
  border: "1px solid rgba(180, 205, 200, 0.45)",
  boxShadow: "0 6px 16px rgba(26, 47, 66, 0.06)",
};
