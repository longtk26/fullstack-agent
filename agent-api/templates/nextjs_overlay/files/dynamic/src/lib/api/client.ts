import { readToken } from "@/lib/auth/token";
import { loadRuntimeConfig } from "@/lib/runtime-config";

/** Where the mock layer answers (MSW), kept apart from the site's own routes. */
export const MOCK_API_BASE = "/mock-api";

export type TApiErrorDetails = unknown;

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: TApiErrorDetails = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type TRequestOptions = {
  query?: Record<string, unknown>;
  body?: unknown;
};

let baseOverride: string | null = null;
let unauthorized: (() => void) | null = null;

/** Tests point the client at a fixed base (`http://localhost/mock-api`). */
export function setApiBase(base: string | null) {
  baseOverride = base;
}

/** Story 22.7: what a 401 does (the app's session clears itself and asks the user to sign in). */
export function onUnauthorized(handler: (() => void) | null) {
  unauthorized = handler;
}

/** Where calls go, and the bearer token they carry: the mock API (the token kept in the browser), the live API
 *  (`local` mode: the token in a header) or the Next server's same-origin proxy (`cookie` mode: it adds the token
 *  from its httpOnly cookie). */
async function target(): Promise<{ base: string; token: string | null }> {
  if (baseOverride !== null) return { base: baseOverride, token: readToken() };
  const config = await loadRuntimeConfig();
  if (config.mockApi) return { base: MOCK_API_BASE, token: readToken() };
  if (config.authTokenStorage === "cookie") return { base: "/api/backend", token: null };
  return { base: config.apiBaseUrl.replace(/\/$/, ""), token: readToken() };
}

/** The only way the frontend talks to the backend: the generated functions in `./operations` call this. */
export async function request<TResponse>(method: string, path: string, options: TRequestOptions = {}): Promise<TResponse> {
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  const { base, token } = await target();
  const url = new URL(`${base}${path}`, origin);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["content-type"] = "application/json";
  if (token) headers.authorization = `Bearer ${token}`;
  const response = await fetch(url, {
    method,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  // a session that no longer works (expired, signed out elsewhere); a wrong password sent no session
  if (response.status === 401 && (token || base === "/api/backend")) unauthorized?.();
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: { code?: string; message?: string; details?: unknown } } | null;
    const error = payload?.error;
    throw new ApiError(response.status, error?.code ?? "HTTP_ERROR", error?.message ?? response.statusText, error?.details ?? null);
  }
  if (response.status === 204) return undefined as TResponse;
  return (await response.json()) as TResponse;
}
