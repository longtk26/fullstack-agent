import { NextResponse, type NextRequest } from "next/server";
import data from "@/content/app.json";
import { cookieMode, publicOrigin, SESSION_COOKIE } from "@/lib/auth/server";

type TApp = {
  auth: { signIn: string } | null;
  access: Record<string, unknown>;
  pages: Record<string, { route: string; sections: { data?: { operationId?: string }; form?: string }[] }>;
  forms: Record<string, { operationId?: string }>;
};

const app = data as unknown as TApp;

/** The pages on an operation behind sign-in, as patterns (`/bookings/[id]` → `^/bookings/[^/]+$`). */
const guarded = Object.values(app.pages)
  .filter((page) => {
    const section = page.sections[0];
    const operation = section?.data?.operationId ?? (section?.form ? app.forms[section.form]?.operationId : undefined);
    return Boolean(operation && app.access[operation]);
  })
  .map((page) => new RegExp(`^${page.route.replace(/\[[^\]]+\]/g, "[^/]+")}$`));

/** Story 22.7, `cookie` mode: a signed-out request for a page behind sign-in goes to the sign-in page on the server
 *  (in `local` mode the browser does it; on the mock API too). */
export function proxy(request: NextRequest) {
  if (!cookieMode() || !app.auth) return NextResponse.next();
  const path = request.nextUrl.pathname;
  if (!guarded.some((pattern) => pattern.test(path)) || request.cookies.get(SESSION_COOKIE)) return NextResponse.next();
  const target = new URL(app.auth.signIn, publicOrigin(request));
  target.searchParams.set("next", path);
  return NextResponse.redirect(target);
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)"],
};
