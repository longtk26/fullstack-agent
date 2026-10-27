"use client";

import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { validateSpec } from "../api/specs-api";
import { parseJson } from "../lib/json-pointer";
import { specKeys } from "../query-keys";
import type { TSpecIssue, TSpecKind } from "../types";

const DEBOUNCE_MS = 500;

/** An issue to show in the editor; parse errors carry a text offset instead of a JSON pointer. */
export type TEditorIssue = TSpecIssue & { offset?: number };

export type TSpecValidation = ReturnType<typeof useSpecValidation>;

/** The `project.mode` a FrontendSpec must declare for the chosen generation mode (the API rejects others). */
function modeIssue(value: unknown, expected: "static" | "dynamic"): TEditorIssue | null {
  const declared = (value as { project?: { mode?: unknown } } | null)?.project?.mode;
  if (declared === undefined || declared === expected) return null;
  const other = expected === "static" ? "Dynamic web app" : "Static website";
  return {
    code: "MODE_INPUT_MISMATCH",
    path: "/project/mode",
    message: `This FrontendSpec is for a ${String(declared)} site; set project.mode to "${expected}" or choose ${other}`,
    hint: null,
    severity: "error",
  };
}

/**
 * Local JSON parse on every keystroke, plus a debounced `POST /specs/validate` (or `/frontend-specs/validate`).
 * `isSubmittable` is true only when the server has validated exactly the current text and found no errors.
 * `expectedMode` adds the FrontendSpec ↔ generation mode check, which the validate endpoint cannot know.
 */
export function useSpecValidation(kind: TSpecKind, text: string, expectedMode?: "static" | "dynamic") {
  const debounced = useDebouncedValue(text, DEBOUNCE_MS);
  const parsed = useMemo(() => (text.trim() ? parseJson(text) : null), [text]);
  const debouncedParsed = useMemo(() => (debounced.trim() ? parseJson(debounced) : null), [debounced]);

  const query = useQuery({
    queryKey: specKeys.validation(kind, debounced),
    queryFn: ({ signal }) => validateSpec(kind, debounced, signal),
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
    const mismatch = parsed?.ok && expectedMode ? modeIssue(parsed.value, expectedMode) : null;
    return [...(mismatch ? [mismatch] : []), ...(report ? [...report.errors, ...report.warnings] : [])];
  }, [parsed, report, expectedMode]);
  const errorCount = issues.filter((issue) => issue.severity === "error").length;

  return {
    parsed: parsed?.ok ? parsed.value : undefined,
    isEmpty: parsed === null,
    issues,
    errorCount,
    warningCount: issues.filter((issue) => issue.severity === "warning").length,
    isChecking,
    requestError: query.error,
    isSubmittable: Boolean(
      parsed?.ok && !isChecking && query.data?.valid && !query.isPlaceholderData && errorCount === 0,
    ),
  };
}
