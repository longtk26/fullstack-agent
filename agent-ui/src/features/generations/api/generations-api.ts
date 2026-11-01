import { apiClient, proxyUrl } from "@/lib/api-client";
import type {
  TArtifact,
  TCreateGenerationPayload,
  TCreateGenerationResult,
  TFileNode,
  TGenerationDetail,
  TGenerationMode,
  TGenerationPage,
  TListFilters,
  TPreview,
  TPreviewAction,
  TPreviewRequest,
  TSpanOutput,
  TSpanStream,
  TTrace,
  TValidationHistory,
  TWorkflowGraph,
} from "../types";

export const PAGE_SIZE = 20;

export function fetchGenerations({ status, cursor }: TListFilters) {
  return apiClient.get<TGenerationPage>("/generations", { query: { status, cursor, limit: PAGE_SIZE } });
}

export function fetchGeneration(id: string) {
  return apiClient.get<TGenerationDetail>(`/generations/${id}`);
}

export function fetchWorkflowGraph(mode: TGenerationMode) {
  return apiClient.get<TWorkflowGraph>("/generations/graph", { query: { mode } });
}

export function createGeneration(payload: TCreateGenerationPayload, idempotencyKey: string) {
  return apiClient.post<TCreateGenerationResult>("/generations", {
    json: payload,
    headers: { "Idempotency-Key": idempotencyKey },
  });
}

export function continueGeneration(
  id: string,
  payload: { backendSpec?: Record<string, unknown> | null; frontendSpec?: Record<string, unknown> | null },
) {
  return apiClient.post<TCreateGenerationResult>(`/generations/${id}/continue`, {
    json: payload,
  });
}

export function cancelGeneration(id: string) {
  return apiClient.post<{ generationId: string; status: string; cancelRequested: boolean }>(
    `/generations/${id}/cancel`,
  );
}

export function generationEventsUrl(id: string) {
  return `/api/proxy/generations/${id}/events`;
}

// -- results (Story 9.5) ------------------------------------------------------------------------------------------

export function fetchValidationHistory(id: string) {
  return apiClient.get<TValidationHistory>(`/generations/${id}/validation`);
}

export function artifactUrl(id: string, artifact: TArtifact) {
  return proxyUrl(`/generations/${id}/artifacts/${artifact.artifactId}`);
}

export function fetchArtifactJson<TData>(id: string, artifactId: string) {
  return apiClient.get<TData>(`/generations/${id}/artifacts/${artifactId}`);
}

export function fetchArtifactText(id: string, artifactId: string) {
  return apiClient.text(`/generations/${id}/artifacts/${artifactId}`);
}

export function fetchFiles(id: string, path: string, source: "backend" | "frontend" = "backend") {
  return apiClient.get<TFileNode>(`/generations/${id}/files`, { query: { path, source } });
}

// -- preview (Story 9.6, 9.8, 9.9) ---------------------------------------------------------------------------------

export function fetchPreview(id: string, kind: "backend" | "frontend" = "backend") {
  return apiClient.get<TPreview>(`/generations/${id}/preview`, { query: { kind } });
}

export function previewAction(id: string, action: TPreviewAction, kind: "backend" | "frontend" = "backend") {
  return apiClient.post<TPreview>(`/generations/${id}/preview/${action}`, { query: { kind } });
}

export function recheckIntegration(id: string) {
  return apiClient.post<TPreview>(`/generations/${id}/integration/recheck`);
}

export function sendUseMocksIntegration(id: string) {
  return apiClient.post<TPreview>(`/generations/${id}/integration/use-mocks`);
}

export function fetchPreviewLogs(id: string, tail = 300, kind: "backend" | "frontend" = "backend") {
  return apiClient.get<{ lines: string[] }>(`/generations/${id}/preview/logs`, { query: { tail, kind } });
}

export function fetchPreviewRequests(id: string) {
  return apiClient.get<{ items: TPreviewRequest[]; cursor: string | null }>(`/generations/${id}/preview/requests`, {
    query: { limit: 500 },
  });
}

// -- trace (Story 9.4) --------------------------------------------------------------------------------------------

export function fetchTrace(id: string) {
  return apiClient.get<TTrace>(`/generations/${id}/trace`);
}

export function fetchSpanOutput(id: string, spanId: string, stream: TSpanStream, tail: number) {
  return apiClient.get<TSpanOutput>(`/generations/${id}/trace/spans/${encodeURIComponent(spanId)}/output`, {
    query: { stream, tail },
  });
}
