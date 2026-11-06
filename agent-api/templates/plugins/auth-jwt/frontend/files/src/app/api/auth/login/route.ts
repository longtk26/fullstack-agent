import { NextResponse, type NextRequest } from "next/server";
import data from "@/content/app.json";
import { backendUrl, refusal, sameOrigin, SESSION_COOKIE, SIGNED_IN_COOKIE, sessionCookie } from "@/lib/auth/server";

const loginPath = (data as { auth: { login: { path: string } } }).auth.login.path;

/** `cookie` mode: signs in at the backend and keeps the token in an httpOnly cookie (Story 22.7). */
export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return refusal(403, "FORBIDDEN", "Cross-site request");
  const response = await fetch(backendUrl(loginPath), {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await request.text(),
  });
  const payload = (await response.json().catch(() => null)) as { accessToken?: string } | null;
  if (!response.ok || !payload?.accessToken) return NextResponse.json(payload, { status: response.ok ? 502 : response.status });
  const out = NextResponse.json({ ok: true });
  out.cookies.set(SESSION_COOKIE, payload.accessToken, sessionCookie(request));
  out.cookies.set(SIGNED_IN_COOKIE, "1", { ...sessionCookie(request), httpOnly: false });
  return out;
}
