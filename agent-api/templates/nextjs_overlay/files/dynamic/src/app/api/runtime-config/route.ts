import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/** `MOCK_TEST_API=false` + `API_BASE_URL=<backend>` switches the browser to the live API (Story 14.2). */
export function GET() {
  return NextResponse.json({
    mockApi: process.env.MOCK_TEST_API !== "false",
    apiBaseUrl: process.env.API_BASE_URL ?? "",
  });
}
