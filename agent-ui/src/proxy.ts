import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_COOKIE_NAME = "bga_token";

export function proxy(request: NextRequest) {
  const isLoggedIn = request.cookies.has(AUTH_COOKIE_NAME);
  const { pathname, search } = request.nextUrl;

  if (pathname === "/login") {
    return isLoggedIn ? NextResponse.redirect(new URL("/generations", request.url)) : NextResponse.next();
  }
  if (!isLoggedIn) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(login);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api/|_next/|favicon.ico|.*\\.[a-z0-9]+$).*)"],
};
