import type { TListFilters } from "./types";

export const generationKeys = {
  all: ["generations"] as const,
  lists: () => [...generationKeys.all, "list"] as const,
  list: (filters: TListFilters) => [...generationKeys.lists(), filters] as const,
  details: () => [...generationKeys.all, "detail"] as const,
  detail: (id: string) => [...generationKeys.details(), id] as const,
  events: (id: string) => [...generationKeys.all, "events", id] as const,
  graph: () => [...generationKeys.all, "graph"] as const,
};
