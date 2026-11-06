import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** `MOCK_TEST_API=false` + `API_BASE_URL=<backend>` switches the browser to the live API (Story 14.2);
 *  `AUTH_TOKEN_STORAGE=cookie` keeps a signed-in user's token in an httpOnly cookie (Story 22.7, decision P8). */
export function GET() {
  return NextResponse.json({
    mockApi: process.env.MOCK_TEST_API !== "false",
    apiBaseUrl: process.env.API_BASE_URL ?? "",
    authTokenStorage: process.env.AUTH_TOKEN_STORAGE === "cookie" ? "cookie" : "local",
  });
}
