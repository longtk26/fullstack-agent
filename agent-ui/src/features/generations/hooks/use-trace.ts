"use client";

import { useEffect, useMemo } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNow } from "@/hooks/use-now";
import { fetchTrace } from "../api/generations-api";
import { isTerminal } from "../lib/status";
import { generationKeys } from "../query-keys";
import type { TGenerationEvent } from "../types";

const REFRESH_TYPES = new Set(["step.started", "step.finished", "engine.finished", "validation.check", "status.changed"]);
const REFRESH_DEBOUNCE_MS = 600;

/** The local trace of a generation (Story 8.3), refetched as SSE step / check events arrive; open spans tick. */
export function useTrace(id: string, status: string, events: TGenerationEvent[]) {
  const queryClient = useQueryClient();
  const running = !isTerminal(status);
  const trace = useQuery({ queryKey: generationKeys.trace(id), queryFn: () => fetchTrace(id) });
  const changes = useMemo(() => events.filter((event) => REFRESH_TYPES.has(event.type)).length, [events]);

  useEffect(() => {
    if (changes === 0) return;
    const timer = setTimeout(
      () => queryClient.invalidateQueries({ queryKey: generationKeys.trace(id) }),
      REFRESH_DEBOUNCE_MS,
    );
    return () => clearTimeout(timer);
  }, [changes, id, queryClient]);

  return { trace, running, now: useNow(running) };
}
