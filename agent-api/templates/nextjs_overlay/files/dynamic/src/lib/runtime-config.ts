/** Read at runtime from the server environment (`MOCK_TEST_API`, `API_BASE_URL`, `AUTH_TOKEN_STORAGE`), so switching
 *  the frontend from mocks to the live API needs a restart, not a rebuild. */
export type TRuntimeConfig = {
  mockApi: boolean;
  apiBaseUrl: string;
  /** Story 22.7 (decision P8): where a signed-in user's token lives: `local` (localStorage, a bearer header) or
   *  `cookie` (an httpOnly cookie the Next server sets; calls go through its `/api/backend` proxy). */
  authTokenStorage: "local" | "cookie";
};

let pending: Promise<TRuntimeConfig> | null = null;

export function loadRuntimeConfig(): Promise<TRuntimeConfig> {
  pending ??= fetch("/api/runtime-config", { cache: "no-store" })
    .then((response) => response.json() as Promise<TRuntimeConfig>)
    .catch(() => ({ mockApi: true, apiBaseUrl: "", authTokenStorage: "local" as const }));
  return pending;
}
