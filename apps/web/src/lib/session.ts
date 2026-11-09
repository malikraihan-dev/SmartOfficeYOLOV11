import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { AdminSession } from "./types";

export async function requireAdmin(): Promise<AdminSession> {
  const token = (await cookies()).get("smartoffice_admin")?.value;
  if (!token) redirect("/login");
  let session: AdminSession;
  try {
    const backend = (process.env.SMARTOFFICE_API_URL ?? "http://127.0.0.1:5000").replace(/\/$/, "");
    const response = await fetch(`${backend}/api/auth/session`, {
      cache: "no-store", headers: { Cookie: `smartoffice_admin=${encodeURIComponent(token)}` }, signal: AbortSignal.timeout(8000),
    });
    if (!response.ok) throw new Error("Session check failed");
    session = await response.json();
  } catch { redirect("/login?reason=server"); }
  if (!session.authenticated || !session.user || !session.csrf_token) redirect("/login?reason=session");
  return session;
}
