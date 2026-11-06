import type { NextRequest } from "next/server";
import { backendUrl, publicBackendHost, refusal, sameOrigin, SESSION_COOKIE } from "@/lib/auth/server";

export const dynamic = "force-dynamic";

type TContext = { params: Promise<{ path: string[] }> };

/** `cookie` mode's same-origin proxy (Story 22.7): the browser's API calls, forwarded to `API_BASE_URL` with the
 *  bearer from the httpOnly cookie. Only this site may call it (`Origin` checked). */
async function forward(request: NextRequest, { params }: TContext) {
  if (!sameOrigin(request)) return refusal(403, "FORBIDDEN", "Cross-site request");
  const { path } = await params;
  const target = new URL(backendUrl(`/${path.map(encodeURIComponent).join("/")}`));
  target.search = request.nextUrl.search;
  const headers = new Headers();
  const type = request.headers.get("content-type");
  if (type) headers.set("content-type", type);
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (token) headers.set("authorization", `Bearer ${token}`);
  const host = publicBackendHost(); // what the backend builds from its address points at its public one
  if (host) {
    headers.set("x-forwarded-host", host);
    headers.set("x-forwarded-proto", new URL(process.env.API_BASE_URL ?? "http://localhost").protocol.replace(":", ""));
  }
  const hasBody = !["GET", "HEAD"].includes(request.method);
  const response = await fetch(target, { method: request.method, headers, body: hasBody ? await request.text() : undefined, redirect: "manual" });
  const out = new Headers();
  const kind = response.headers.get("content-type");
  if (kind) out.set("content-type", kind);
  return new Response(response.status === 204 ? null : response.body, { status: response.status, headers: out });
}

export { forward as DELETE, forward as GET, forward as PATCH, forward as POST, forward as PUT };
