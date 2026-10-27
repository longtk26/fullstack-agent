/** Read at runtime from the server environment (`MOCK_TEST_API`, `API_BASE_URL`), so switching the frontend from
 *  mocks to the live API needs a restart, not a rebuild. */
export type TRuntimeConfig = {
  mockApi: boolean;
  apiBaseUrl: string;
};

let pending: Promise<TRuntimeConfig> | null = null;

export function loadRuntimeConfig(): Promise<TRuntimeConfig> {
  pending ??= fetch("/api/runtime-config", { cache: "no-store" })
    .then((response) => response.json() as Promise<TRuntimeConfig>)
    .catch(() => ({ mockApi: true, apiBaseUrl: "" }));
  return pending;
}
