"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { fetchGenerations } from "../api/generations-api";
import { isTerminal } from "../lib/status";
import { generationKeys } from "../query-keys";
import type { TListFilters } from "../types";

const ACTIVE_REFETCH_MS = 5000;

export function useGenerations(filters: TListFilters) {
  return useQuery({
    queryKey: generationKeys.list(filters),
    queryFn: () => fetchGenerations(filters),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => !isTerminal(item.status)) ? ACTIVE_REFETCH_MS : false,
  });
}
