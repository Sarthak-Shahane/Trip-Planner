/**
 * Backend base URL (Flask). Must match TRIP_PLANNER_PUBLIC_URL in backend/.env for image URLs.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5000"
).replace(/\/$/, "")

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`
  return `${API_BASE_URL}${p}`
}
