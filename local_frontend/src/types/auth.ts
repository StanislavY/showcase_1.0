/** Result of a courier login attempt returned by the backend. */
export interface CourierLoginResponse {
  success: boolean;
  token: string | null;
  courier_id: string | null;
  message: string;
}

/** Result of an admin login attempt returned by the backend. */
export interface AdminLoginResponse {
  success: boolean;
  token: string | null;
  admin_id: string | null;
  message: string;
}
