// @vitest-environment node
// Story 22.4: the mock API answers the contract's scenarios (`x-bga.scenarios`) as the backend does, so an app behaves
// the same on mocks and live. Run by the frontend lane's `scenarios` check; `src/mocks/scenarios.json` is generated
// with the scenarios the mocks emulate (the others are listed there under `notEmulated`).
import { setupServer } from "msw/node";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { MOCK_API_BASE } from "@/lib/api/client";
import { handlers, resetMockStore } from "./handlers";
import data from "./scenarios.json";

type TScenario = {
  operationId: string;
  method: string;
  path: string;
  name: string;
  params?: Record<string, unknown>;
  body?: unknown;
  /** Story 22.7: run signed in (as `user`, else the contract's login), as the backend's smoke check does. */
  auth?: boolean;
  user?: string;
  expect: { status: number; code?: string };
};

type TLogin = { path: string; body: Record<string, unknown>; field: string };

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
beforeEach(() => resetMockStore());
afterAll(() => server.close());

function url(scenario: TScenario): string {
  let path = scenario.path;
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(scenario.params ?? {})) {
    if (path.includes(`{${name}}`)) path = path.replace(`{${name}}`, encodeURIComponent(String(value)));
    else if (value !== undefined && value !== null) query.set(name, String(value));
  }
  const search = query.toString();
  return `http://localhost${MOCK_API_BASE}${path}${search ? `?${search}` : ""}`;
}

/** A demo user's token from the mock API's login (the one the scenario names, else the contract's). */
async function tokenFor(scenario: TScenario): Promise<string | null> {
  const login = (data as { login?: TLogin }).login;
  if (!scenario.auth || !login) return null;
  const body = { ...login.body, ...(scenario.user ? { [login.field]: scenario.user } : {}) };
  const response = await fetch(`http://localhost${MOCK_API_BASE}${login.path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return ((await response.json()) as { accessToken?: string }).accessToken ?? null;
}

describe("the mock API answers the contract's scenarios", () => {
  const scenarios = (data as { scenarios: TScenario[] }).scenarios;
  it.each(scenarios.map((scenario) => [`${scenario.operationId}: ${scenario.name}`, scenario] as const))("%s", async (_, scenario) => {
    const token = await tokenFor(scenario);
    const response = await fetch(url(scenario), {
      method: scenario.method,
      headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
      body: scenario.body === undefined ? undefined : JSON.stringify(scenario.body),
    });
    expect(response.status, `${scenario.method} ${scenario.path}`).toBe(scenario.expect.status);
    if (scenario.expect.code) {
      const payload = (await response.json()) as { error?: { code?: string } };
      expect(payload.error?.code).toBe(scenario.expect.code);
    }
  });
});
