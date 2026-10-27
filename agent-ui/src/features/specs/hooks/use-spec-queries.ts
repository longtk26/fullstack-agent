"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchEngines, fetchExampleIndex, fetchSpecSchema, importFrontendSite } from "../api/specs-api";
import { specKeys } from "../query-keys";
import type { TSpecKind } from "../types";

export function useSpecSchema(kind: TSpecKind) {
  return useQuery({ queryKey: specKeys.schema(kind), queryFn: () => fetchSpecSchema(kind), staleTime: Infinity });
}

export function useExampleIndex() {
  return useQuery({ queryKey: specKeys.examples(), queryFn: fetchExampleIndex, staleTime: Infinity });
}

export function useEngines() {
  return useQuery({ queryKey: specKeys.engines(), queryFn: fetchEngines, staleTime: 30_000 });
}

export function useFrontendImport() {
  return useMutation({
    mutationFn: ({ raw, includeAdminCrud }: { raw: string; includeAdminCrud: boolean }) =>
      importFrontendSite(raw, includeAdminCrud),
  });
}
