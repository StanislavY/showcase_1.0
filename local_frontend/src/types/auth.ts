/** Result of a courier login attempt returned by the backend. */
export interface CourierLoginResponse {
  success: boolean;
  token: string | null;
  courier_id: string | null;
  message: string;
}
