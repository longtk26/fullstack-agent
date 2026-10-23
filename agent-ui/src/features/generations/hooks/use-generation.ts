"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchGeneration, fetchWorkflowGraph } from "../api/generations-api";
import { generationKeys } from "../query-keys";

export function useGeneration(id: string) {
  return useQuery({
    queryKey: generationKeys.detail(id),
    queryFn: () => fetchGeneration(id),
  });
}

export function useWorkflowGraph() {
  return useQuery({
    queryKey: generationKeys.graph(),
    queryFn: fetchWorkflowGraph,
    staleTime: Infinity,
  });
}
