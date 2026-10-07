export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export async function api(path: string, opts?: RequestInit) {
  const r = await fetch(API + path, { ...opts, headers: { "Content-Type": "application/json" } });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
