/**
 * Single source of truth for the postamat working mode.
 *
 * The mode is intentionally modelled as one enum (not two booleans) so the
 * application can never reach a contradictory state (both modes on / both
 * off). It is persisted in `localStorage` so the choice survives reloads.
 */

export type TerminalMode = "kiosk" | "online_sales";

export const TERMINAL_MODE_KEY = "terminal_mode";

const DEFAULT_TERMINAL_MODE: TerminalMode = "kiosk";

function isTerminalMode(value: string | null): value is TerminalMode {
  return value === "kiosk" || value === "online_sales";
}

/**
 * Returns the stored mode. Falls back to `kiosk` when nothing is stored or the
 * stored value is unknown, so the app always has exactly one valid mode.
 */
export function getTerminalMode(): TerminalMode {
  try {
    const stored = localStorage.getItem(TERMINAL_MODE_KEY);
    return isTerminalMode(stored) ? stored : DEFAULT_TERMINAL_MODE;
  } catch {
    return DEFAULT_TERMINAL_MODE;
  }
}

/** Persists the selected mode in `localStorage`. */
export function setTerminalMode(mode: TerminalMode): void {
  try {
    localStorage.setItem(TERMINAL_MODE_KEY, mode);
  } catch {
    /* storage may be unavailable; the in-memory state still updates */
  }
}
