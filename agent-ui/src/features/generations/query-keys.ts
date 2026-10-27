import type { TListFilters } from "./types";

export const generationKeys = {
  all: ["generations"] as const,
  lists: () => [...generationKeys.all, "list"] as const,
  list: (filters: TListFilters) => [...generationKeys.lists(), filters] as const,
  details: () => [...generationKeys.all, "detail"] as const,
  detail: (id: string) => [...generationKeys.details(), id] as const,
  events: (id: string) => [...generationKeys.all, "events", id] as const,
  graph: () => [...generationKeys.all, "graph"] as const,
  validation: (id: string) => [...generationKeys.all, "validation", id] as const,
  artifact: (id: string, artifactId: string) => [...generationKeys.all, "artifact", id, artifactId] as const,
  files: (id: string, path: string) => [...generationKeys.all, "files", id, path] as const,
  preview: (id: string) => [...generationKeys.all, "preview", id] as const,
  previewLogs: (id: string) => [...generationKeys.all, "preview-logs", id] as const,
  previewRequests: (id: string) => [...generationKeys.all, "preview-requests", id] as const,
  trace: (id: string) => [...generationKeys.all, "trace", id] as const,
  spanOutput: (id: string, spanId: string, stream: string, tail: number) =>
    [...generationKeys.all, "span-output", id, spanId, stream, tail] as const,
};
