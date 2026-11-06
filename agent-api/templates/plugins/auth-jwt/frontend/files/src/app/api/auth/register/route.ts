import { NextResponse, type NextRequest } from "next/server";
import data from "@/content/app.json";
import { backendUrl, refusal, sameOrigin, SESSION_COOKIE, SIGNED_IN_COOKIE, sessionCookie } from "@/lib/auth/server";

const auth = (data as { auth: { login: { path: string }; register: { path: string }; loginField: string } }).auth;

async function post(path: string, body: unknown) {
  return fetch(backendUrl(path), { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
}

/** `cookie` mode: creates the account at the backend, signs in with it and keeps the token in an httpOnly cookie. */
export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return refusal(403, "FORBIDDEN", "Cross-site request");
  const values = (await request.json().catch(() => ({}))) as Record<string, unknown>;
  const created = await post(auth.register.path, values);
  if (!created.ok) return NextResponse.json(await created.json().catch(() => null), { status: created.status });
  const login = await post(auth.login.path, { [auth.loginField]: values[auth.loginField], password: values.password });
  const payload = (await login.json().catch(() => null)) as { accessToken?: string } | null;
  if (!login.ok || !payload?.accessToken) return NextResponse.json(payload, { status: login.ok ? 502 : login.status });
  const out = NextResponse.json({ ok: true }, { status: 201 });
  out.cookies.set(SESSION_COOKIE, payload.accessToken, sessionCookie(request));
  out.cookies.set(SIGNED_IN_COOKIE, "1", { ...sessionCookie(request), httpOnly: false });
  return out;
}
