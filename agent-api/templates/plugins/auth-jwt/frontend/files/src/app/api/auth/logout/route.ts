import { NextResponse, type NextRequest } from "next/server";
import { refusal, sameOrigin, SESSION_COOKIE, SIGNED_IN_COOKIE } from "@/lib/auth/server";

/** `cookie` mode: forgets the session (the backend's tokens are stateless; the cookie is the session). */
export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return refusal(403, "FORBIDDEN", "Cross-site request");
  const out = NextResponse.json({ ok: true });
  out.cookies.delete(SESSION_COOKIE);
  out.cookies.delete(SIGNED_IN_COOKIE);
  return out;
}
