"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchGeneration, fetchWorkflowGraph } from "../api/generations-api";
import { generationKeys } from "../query-keys";
import type { TGenerationMode } from "../types";

export function useGeneration(id: string) {
  return useQuery({
    queryKey: generationKeys.detail(id),
    queryFn: () => fetchGeneration(id),
  });
}

export function useWorkflowGraph(mode: TGenerationMode | undefined) {
  return useQuery({
    queryKey: generationKeys.graph(mode ?? "backend"),
    queryFn: () => fetchWorkflowGraph(mode ?? "backend"),
    enabled: mode !== undefined,
    staleTime: Infinity,
  });
}
