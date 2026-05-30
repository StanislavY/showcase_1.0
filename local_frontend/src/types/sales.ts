/** Current sales-limit snapshot returned by the backend.
 *
 * All amounts are integers in kopecks (1 rouble = 100 kopecks) so there
 * are no rounding errors. The UI converts them to roubles for display.
 */
export interface SalesLimitSummary {
  limit_id: number | null;
  limit_amount_kopecks: number;
  sold_amount_kopecks: number;
  remaining_amount_kopecks: number;
  status: string;
}

/** Result of a sell-from-cell attempt returned by the backend.
 *
 * On both success and a business-rule failure (empty cell, exhausted
 * limit, hardware error) the backend returns this same shape; the UI
 * branches on ``success`` and always shows ``message`` to the customer.
 */
export interface SaleResponse {
  success: boolean;
  message: string;
  sale: unknown | null;
  limit_summary: SalesLimitSummary | null;
}
