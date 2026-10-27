"use client";

import { useCallback, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useSpecDraftHydrated, useSpecDraftStore } from "@/store/spec-draft-store";
import type { TGenerationMode } from "../types";

const MODES: TGenerationMode[] = ["static", "dynamic", "backend"];

function parseMode(value: string | null): TGenerationMode | null {
  return MODES.includes(value as TGenerationMode) ? (value as TGenerationMode) : null;
}

/** The mode of the generation being set up: `?mode=` wins, else the draft store (default `backend`). */
export function useGenerationMode() {
  const urlMode = parseMode(useSearchParams().get("mode"));
  const storedMode = useSpecDraftStore((state) => state.mode);
  const storeMode = useSpecDraftStore((state) => state.setMode);
  const hydrated = useSpecDraftHydrated();
  const mode = urlMode ?? storedMode;

  // Only after rehydration: an earlier write would persist the empty initial draft over the saved one.
  useEffect(() => {
    if (hydrated && urlMode && urlMode !== storedMode) storeMode(urlMode);
  }, [hydrated, urlMode, storedMode, storeMode]);

  const setMode = useCallback(
    (next: TGenerationMode) => {
      storeMode(next);
      const params = new URLSearchParams(window.location.search);
      params.set("mode", next);
      window.history.replaceState(null, "", `?${params}`);
    },
    [storeMode],
  );

  return { mode, setMode };
}
