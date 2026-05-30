/** Money helpers. Amounts are integer kopecks on the wire (1 ₽ = 100 коп.). */

/**
 * Format an integer kopecks amount as a rouble string.
 *
 * @example kopecksToRublesText(12345) // "123,45 ₽"
 */
export function kopecksToRublesText(value: number): string {
  const rubles = value / 100;
  const formatted = rubles.toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${formatted} ₽`;
}

/** Format a product price stored in roubles on the backend. */
export function rublesToText(value: number): string {
  const formatted = value.toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return `${formatted} ₽`;
}

/**
 * Convert a whole-rouble keypad string into kopecks.
 *
 * For the MVP only whole roubles are entered (no kopecks), so any
 * non-digit characters are dropped before parsing.
 *
 * @example rublesInputToKopecks("1500") // 150000
 */
export function rublesInputToKopecks(value: string): number {
  const digits = value.replace(/\D/g, "");
  if (digits === "") return 0;
  return Number.parseInt(digits, 10) * 100;
}
