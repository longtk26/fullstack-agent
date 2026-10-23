import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import { API_URL, AUTH_COOKIE_NAME } from "@/lib/server-config";

const FORWARDED_REQUEST_HEADERS = ["accept", "content-type", "idempotency-key", "last-event-id"];
const FORWARDED_RESPONSE_HEADERS = ["content-type", "cache-control", "retry-after", "x-request-id"];

type ProxyContext = { params: Promise<{ path: string[] }> };

async function forward(request: NextRequest, { params }: ProxyContext): Promise<Response> {
  const { path } = await params;
  const target = new URL(`${API_URL}/api/v1/${path.map(encodeURIComponent).join("/")}`);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  for (const name of FORWARDED_REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (token) headers.set("authorization", `Bearer ${token}`);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: hasBody ? await request.arrayBuffer() : undefined,
      signal: request.signal,
      cache: "no-store",
    });
  } catch {
    return Response.json(
      { error: { code: "UPSTREAM_UNAVAILABLE", message: "The agent API is unreachable" } },
      { status: 502 },
    );
  }

  const responseHeaders = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  if (upstream.headers.get("content-type")?.startsWith("text/event-stream")) {
    responseHeaders.set("cache-control", "no-cache, no-transform");
    responseHeaders.set("x-accel-buffering", "no");
  }
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export const GET = forward;
export const POST = forward;
export const PUT = forward;
export const PATCH = forward;
export const DELETE = forward;
