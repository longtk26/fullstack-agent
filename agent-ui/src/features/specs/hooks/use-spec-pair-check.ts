"use client";

import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { checkSpecPair } from "../api/specs-api";
import { specKeys } from "../query-keys";
import type { TSpecValidation } from "./use-spec-validation";

/**
 * Frontend ↔ contract consistency of the two editors (`POST /frontend-specs/check-pair`). Runs only once both
 * specs are valid (and `active`: dynamic mode), on exactly the texts that were validated, so it inherits their debounce.
 */
export function useSpecPairCheck(
  active: boolean,
  frontend: TSpecValidation & { text: string },
  backend: TSpecValidation & { text: string },
) {
  const enabled = active && frontend.isSubmittable && backend.isSubmittable;
  const query = useQuery({
    queryKey: specKeys.pair(frontend.text, backend.text),
    queryFn: ({ signal }) => checkSpecPair(frontend.parsed, backend.parsed, signal),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });
  const report = enabled && !query.isPlaceholderData ? query.data : undefined;
  const issues = useMemo(() => (report ? [...report.errors, ...report.warnings] : []), [report]);

  return {
    /** Whether the check can run at all (both specs valid). */
    isReady: enabled,
    isChecking: enabled && query.isFetching,
    issues,
    errorCount: report?.errors.length ?? 0,
    requestError: query.error,
    /** The BackendSpec's API contract once the pair was checked (read-only preview, Story 9.7b). */
    contract: report?.checked ? (report.contract ?? null) : null,
    // A static FrontendSpec is not checked (`checked: false`); dynamic mode needs a checked, consistent pair.
    isSubmittable: Boolean(report?.checked && report.valid && !query.isFetching),
  };
}
