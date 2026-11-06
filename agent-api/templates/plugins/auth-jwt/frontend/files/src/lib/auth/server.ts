import type { NextRequest } from "next/server";

/** Story 22.7, `cookie` mode (decision P8): the Next server holds the user's token in an httpOnly, `SameSite=Lax`
 *  cookie, signs in and out through the backend, and forwards the browser's calls with the bearer. */
export const SESSION_COOKIE = "bga_session";
/** Readable by the page (not the token): whether there is a session to ask the backend about. */
export const SIGNED_IN_COOKIE = "bga_signed_in";
const SESSION_SECONDS = 60 * 60; // the backend's tokens last an hour

export function cookieMode(): boolean {
  return process.env.AUTH_TOKEN_STORAGE === "cookie" && process.env.MOCK_TEST_API === "false";
}

/** The backend as this server reaches it: `API_INTERNAL_URL` when the browser's address (`API_BASE_URL`) is not
 *  reachable from here (a container), else `API_BASE_URL`. */
export function backendUrl(path: string): string {
  const base = process.env.API_INTERNAL_URL || process.env.API_BASE_URL || "";
  return `${base.replace(/\/$/, "")}${path}`;
}

/** The address the browser used (behind a published port, `request.url` names the server's own). */
export function publicOrigin(request: NextRequest): string {
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host") ?? request.nextUrl.host;
  const protocol = request.headers.get("x-forwarded-proto") ?? request.nextUrl.protocol.replace(":", "");
  return `${protocol}://${host}`;
}

/** The host the backend is told it is called by (`X-Forwarded-Host`): the browser's address for it (`API_BASE_URL`), so what it builds from its
 *  own address (a checkout page's link) points where the browser can go, even when this server reaches it by another
 *  name (`API_INTERNAL_URL`). */
export function publicBackendHost(): string | null {
  try {
    return process.env.API_INTERNAL_URL && process.env.API_BASE_URL ? new URL(process.env.API_BASE_URL).host : null;
  } catch {
    return null;
  }
}

export function sessionCookie(request: NextRequest) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: publicOrigin(request).startsWith("https:"),
    path: "/",
    maxAge: SESSION_SECONDS,
  };
}

/** Only this site's pages may call the proxy and the auth routes (a cross-site form or script is refused). */
export function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  return !origin || new URL(origin).host === new URL(publicOrigin(request)).host;
}

export function refusal(status: number, code: string, message: string): Response {
  return Response.json({ error: { code, message, details: null } }, { status });
}
