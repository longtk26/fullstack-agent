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

/** Tests point the client at a fixed base (`http://localhost/mock-api`). */
export function setApiBase(base: string | null) {
  baseOverride = base;
}

async function apiBase(): Promise<string> {
  if (baseOverride !== null) return baseOverride;
  const config = await loadRuntimeConfig();
  return config.mockApi ? MOCK_API_BASE : config.apiBaseUrl.replace(/\/$/, "");
}

/** The only way the frontend talks to the backend: the generated functions in `./operations` call this. */
export async function request<TResponse>(method: string, path: string, options: TRequestOptions = {}): Promise<TResponse> {
  const origin = typeof window === "undefined" ? "http://localhost" : window.location.origin;
  const url = new URL(`${await apiBase()}${path}`, origin);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  const response = await fetch(url, {
    method,
    headers: options.body === undefined ? undefined : { "content-type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error?: { code?: string; message?: string; details?: unknown } } | null;
    const error = payload?.error;
    throw new ApiError(response.status, error?.code ?? "HTTP_ERROR", error?.message ?? response.statusText, error?.details ?? null);
  }
  if (response.status === 204) return undefined as TResponse;
  return (await response.json()) as TResponse;
}
