import { apiClient } from "@/lib/api-client";
import type { TEngineList, TExampleIndex, TFrontendImportResult, TValidationReport } from "../types";

export function validateSpec(raw: string, signal?: AbortSignal) {
  return apiClient.post<TValidationReport>("/specs/validate", { rawBody: raw, signal });
}

export function fetchSpecSchema() {
  return apiClient.get<Record<string, unknown>>("/specs/schema");
}

export function importFrontendSite(raw: string, includeAdminCrud: boolean) {
  return apiClient.post<TFrontendImportResult>("/spec-imports/frontend", {
    rawBody: raw,
    query: { includeAdminCrud },
  });
}

export function fetchEngines() {
  return apiClient.get<TEngineList>("/engines");
}

async function fetchStatic<TData>(path: string): Promise<TData> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return (await response.json()) as TData;
}

export function fetchExampleIndex() {
  return fetchStatic<TExampleIndex>("/examples/index.json");
}

export async function fetchExampleText(path: string): Promise<string> {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`Could not load ${path}`);
  return response.text();
}
