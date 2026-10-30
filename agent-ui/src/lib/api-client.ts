import { logoutAction } from "@/lib/auth-actions";
import type { TApiErrorBody } from "@/types/api";

export const PROXY_BASE = "/api/proxy";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type TRequestOptions = Omit<RequestInit, "body"> & {
  json?: unknown;
  rawBody?: string;
  /** Multipart upload; the browser sets the content type with its boundary. */
  form?: FormData;
  query?: Record<string, string | number | boolean | null | undefined>;
};

async function send(path: string, { json, rawBody, form, query, headers, ...init }: TRequestOptions = {}) {
  const url = new URL(`${PROXY_BASE}${path}`, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  }
  const body = json !== undefined ? JSON.stringify(json) : rawBody;
  const response = await fetch(url, {
    ...init,
    body: form ?? body,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(headers as Record<string, string> | undefined),
    },
  });

  if (response.status === 401) {
    await logoutAction();
  }
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as TApiErrorBody | null;
    throw new ApiError(
      response.status,
      error?.error?.code ?? "HTTP_ERROR",
      error?.error?.message ?? `Request failed with status ${response.status}`,
      error?.error?.details,
    );
  }
  return response;
}

async function request<TData>(path: string, options: TRequestOptions = {}) {
  const response = await send(path, options);
  if (response.status === 204 || response.headers.get("content-length") === "0") return undefined as TData;
  return (await response.json()) as TData;
}

export const apiClient = {
  get: <TData>(path: string, options?: TRequestOptions) => request<TData>(path, { ...options, method: "GET" }),
  post: <TData>(path: string, options?: TRequestOptions) => request<TData>(path, { ...options, method: "POST" }),
  delete: <TData>(path: string, options?: TRequestOptions) => request<TData>(path, { ...options, method: "DELETE" }),
  text: async (path: string, options?: TRequestOptions) =>
    (await send(path, { ...options, method: "GET", headers: { Accept: "*/*", ...options?.headers } })).text(),
};

/** Same-origin URL for a plain link (downloads); the BFF proxy adds the auth cookie as a bearer token. */
export function proxyUrl(path: string): string {
  return `${PROXY_BASE}${path}`;
}
