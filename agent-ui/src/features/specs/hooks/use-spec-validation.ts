"use client";

import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { validateSpec } from "../api/specs-api";
import { parseJson } from "../lib/json-pointer";
import { specKeys } from "../query-keys";
import type { TSpecIssue } from "../types";

const DEBOUNCE_MS = 500;

/** An issue to show in the editor; parse errors carry a text offset instead of a JSON pointer. */
export type TEditorIssue = TSpecIssue & { offset?: number };

/**
 * Local JSON parse on every keystroke, plus a debounced `POST /specs/validate`. `isSubmittable` is true
 * only when the server has validated exactly the current text and found no errors.
 */
export function useSpecValidation(text: string) {
  const debounced = useDebouncedValue(text, DEBOUNCE_MS);
  const parsed = useMemo(() => (text.trim() ? parseJson(text) : null), [text]);
  const debouncedParsed = useMemo(() => (debounced.trim() ? parseJson(debounced) : null), [debounced]);

  const query = useQuery({
    queryKey: specKeys.validation(debounced),
    queryFn: ({ signal }) => validateSpec(debounced, signal),
    enabled: debouncedParsed?.ok === true,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });

  const isChecking = text !== debounced || query.isFetching;
  const report = parsed?.ok ? query.data : undefined;

  const issues: TEditorIssue[] = useMemo(() => {
    if (parsed && !parsed.ok) {
      return [
        { code: "JSON_MALFORMED", path: "", message: parsed.message, hint: null, severity: "error", offset: parsed.offset },
      ];
    }
    return report ? [...report.errors, ...report.warnings] : [];
  }, [parsed, report]);

  return {
    parsed: parsed?.ok ? parsed.value : undefined,
    isEmpty: parsed === null,
    issues,
    errorCount: issues.filter((issue) => issue.severity === "error").length,
    warningCount: issues.filter((issue) => issue.severity === "warning").length,
    isChecking,
    requestError: query.error,
    isSubmittable: Boolean(parsed?.ok && !isChecking && query.data?.valid && !query.isPlaceholderData),
  };
}
