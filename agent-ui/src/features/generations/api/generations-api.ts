import { apiClient } from "@/lib/api-client";
import type {
  TCreateGenerationPayload,
  TCreateGenerationResult,
  TGenerationDetail,
  TGenerationPage,
  TListFilters,
  TWorkflowGraph,
} from "../types";

export const PAGE_SIZE = 20;

export function fetchGenerations({ status, cursor }: TListFilters) {
  return apiClient.get<TGenerationPage>("/generations", { query: { status, cursor, limit: PAGE_SIZE } });
}

export function fetchGeneration(id: string) {
  return apiClient.get<TGenerationDetail>(`/generations/${id}`);
}

export function fetchWorkflowGraph() {
  return apiClient.get<TWorkflowGraph>("/generations/graph");
}

export function createGeneration(payload: TCreateGenerationPayload, idempotencyKey: string) {
  return apiClient.post<TCreateGenerationResult>("/generations", {
    json: payload,
    headers: { "Idempotency-Key": idempotencyKey },
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
