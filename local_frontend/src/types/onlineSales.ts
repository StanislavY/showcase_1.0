/** Structured result of the online-sales pickup ("Забрать товар") scenario.
 *
 * The local backend always answers HTTP 200 and encodes every outcome
 * (in-progress, cloud offline, no products, completed, partial failure) in
 * this body. The frontend never decides business rules: it branches on
 * ``code`` / ``success`` and shows ``message`` (and ``next_action`` when
 * present) to the customer.
 *
 * ``code`` values mirror the backend constants, e.g. ``PICKUP_COMPLETED``,
 * ``CLOUD_UNAVAILABLE``, ``NO_PRODUCTS_TO_PICKUP``, ``ISSUE_FAILED``,
 * ``PICKUP_FAILED``, ``OPERATION_ALREADY_IN_PROGRESS``.
 */
export interface OnlineSalesPickupResponse {
  success: boolean;
  code: string;
  message: string;
  next_action?: string;
  opened_cells?: number[];
  failed_cells?: number[];
}

/** Backend code returned when the cloud is unreachable. */
export const ONLINE_SALES_CLOUD_UNAVAILABLE = "CLOUD_UNAVAILABLE";
