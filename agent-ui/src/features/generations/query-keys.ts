import type { TListFilters } from "./types";

export const generationKeys = {
  all: ["generations"] as const,
  lists: () => [...generationKeys.all, "list"] as const,
  list: (filters: TListFilters) => [...generationKeys.lists(), filters] as const,
  details: () => [...generationKeys.all, "detail"] as const,
  detail: (id: string) => [...generationKeys.details(), id] as const,
  events: (id: string) => [...generationKeys.all, "events", id] as const,
  graph: (mode: string) => [...generationKeys.all, "graph", mode] as const,
  validation: (id: string) => [...generationKeys.all, "validation", id] as const,
  artifact: (id: string, artifactId: string) => [...generationKeys.all, "artifact", id, artifactId] as const,
  files: (id: string, path: string, source: "backend" | "frontend" = "backend") =>
    [...generationKeys.all, "files", id, source, path] as const,
  preview: (id: string, kind: "backend" | "frontend" = "backend") =>
    [...generationKeys.all, "preview", id, kind] as const,
  previewLogs: (id: string, kind: "backend" | "frontend" = "backend") =>
    [...generationKeys.all, "preview-logs", id, kind] as const,
  previewRequests: (id: string) => [...generationKeys.all, "preview-requests", id] as const,
  trace: (id: string) => [...generationKeys.all, "trace", id] as const,
  spanOutput: (id: string, spanId: string, stream: string, tail: number) =>
    [...generationKeys.all, "span-output", id, spanId, stream, tail] as const,
};
