import { apiClient } from "@/lib/api-client";
import type {
  TEngineList,
  TExampleIndex,
  TFrontendImportResult,
  TSpecKind,
  TSpecPairReport,
  TValidationReport,
} from "../types";

const SPEC_ROUTES: Record<TSpecKind, string> = { backend: "/specs", frontend: "/frontend-specs" };

export function validateSpec(kind: TSpecKind, raw: string, signal?: AbortSignal) {
  return apiClient.post<TValidationReport>(`${SPEC_ROUTES[kind]}/validate`, { rawBody: raw, signal });
}

export function fetchSpecSchema(kind: TSpecKind) {
  return apiClient.get<Record<string, unknown>>(`${SPEC_ROUTES[kind]}/schema`);
}

export function checkSpecPair(frontendSpec: unknown, backendSpec: unknown, signal?: AbortSignal) {
  return apiClient.post<TSpecPairReport>("/frontend-specs/check-pair", { json: { frontendSpec, backendSpec }, signal });
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
