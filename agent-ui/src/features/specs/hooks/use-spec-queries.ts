"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchEngines, fetchExampleIndex, fetchSpecSchema, importFrontendSite } from "../api/specs-api";
import { specKeys } from "../query-keys";

export function useSpecSchema() {
  return useQuery({ queryKey: specKeys.schema(), queryFn: fetchSpecSchema, staleTime: Infinity });
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
